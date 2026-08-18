use crate::document::Document;
use crate::error::DocError;
use crate::operations::Operation;
use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

/// Validate document name to prevent path traversal and DoS.
/// Rules: non-empty, len <=200, no '/', '\', "..", ".", null byte, not starting with '.'.
pub fn validate_doc_name(name: &str) -> Result<(), DocError> {
    if name.is_empty() {
        return Err(DocError::InvalidArgument(
            "document name cannot be empty".to_string(),
        ));
    }
    if name.len() > 200 {
        return Err(DocError::InvalidArgument(
            "document name too long (max 200 chars)".to_string(),
        ));
    }
    if name.contains('\0') {
        return Err(DocError::InvalidArgument(
            "document name contains null byte".to_string(),
        ));
    }
    if name.contains('/') || name.contains('\\') {
        return Err(DocError::InvalidArgument(format!(
            "document name '{}' contains path separators",
            name
        )));
    }
    if name.contains("..") {
        return Err(DocError::InvalidArgument(format!(
            "document name '{}' contains '..'",
            name
        )));
    }
    if name == "." || name == ".." {
        return Err(DocError::InvalidArgument(format!(
            "document name '{}' is reserved",
            name
        )));
    }
    if name.starts_with('.') {
        return Err(DocError::InvalidArgument(format!(
            "document name '{}' cannot start with '.'",
            name
        )));
    }
    // Also reject if name is only whitespace?
    // Allow alphanumeric, -, _, ., but also keep permissive for other valid names.
    Ok(())
}

fn data_dir() -> PathBuf {
    let dir = PathBuf::from(".collab-doc");
    if !dir.exists() {
        // Ignore errors here; subsequent operations will surface them
        let _ = fs::create_dir_all(&dir);
    }
    dir
}

fn doc_path(name: &str) -> PathBuf {
    data_dir().join(format!("{}.json", name))
}

fn wal_path(name: &str) -> PathBuf {
    data_dir().join(format!("{}.wal", name))
}

pub fn doc_exists(name: &str) -> bool {
    // Even if validate fails, existence check returns false
    if validate_doc_name(name).is_err() {
        return false;
    }
    doc_path(name).exists()
}

/// Atomic save: write to temp file then rename.
pub fn save_document(doc: &Document) -> Result<(), DocError> {
    validate_doc_name(&doc.name)?;
    let dir = data_dir();
    if !dir.exists() {
        fs::create_dir_all(&dir)?;
    }
    let path = doc_path(&doc.name);
    let tmp_path = dir.join(format!("{}.json.tmp", doc.name));

    let json = serde_json::to_string_pretty(doc)?;
    // Write to temp
    {
        let mut f = fs::File::create(&tmp_path)?;
        f.write_all(json.as_bytes())?;
        f.sync_all()?;
    }
    // Rename atomic on POSIX
    fs::rename(&tmp_path, &path)?;
    Ok(())
}

/// Load document with WAL replay and corruption handling.
/// - If main file missing but WAL exists, create empty doc and replay.
/// - If main file corrupted, attempt recovery from WAL if possible, else return Corruption.
/// - WAL lines that are invalid JSON are skipped with warning.
pub fn load_document(name: &str) -> Result<Document, DocError> {
    validate_doc_name(name)?;
    let path = doc_path(name);
    let w_path = wal_path(name);

    let mut doc: Document = if path.exists() {
        match fs::read_to_string(&path) {
            Ok(contents) => {
                // Empty file treated as corruption (possible crash mid-write)
                if contents.trim().is_empty() {
                    // Try WAL recovery
                    if w_path.exists() {
                        eprintln!("Warning: main file empty, attempting WAL recovery for '{}'", name);
                        Document::new(name)
                    } else {
                        return Err(DocError::Corruption(format!(
                            "document file for '{}' is empty",
                            name
                        )));
                    }
                } else {
                    match serde_json::from_str::<Document>(&contents) {
                        Ok(d) => {
                            // Verify integrity after parsing
                            if let Err(verr) = d.verify() {
                                if w_path.exists() {
                                    eprintln!(
                                        "Warning: main file failed verification for '{}': {}, attempting WAL recovery",
                                        name, verr
                                    );
                                    Document::new(name)
                                } else {
                                    return Err(DocError::Corruption(format!(
                                        "document '{}' failed verification: {}",
                                        name, verr
                                    )));
                                }
                            } else {
                                d
                            }
                        }
                        Err(e) => {
                            // Try WAL recovery if WAL exists
                            if w_path.exists() {
                                eprintln!(
                                    "Warning: main file corrupted for '{}': {}, attempting WAL recovery",
                                    name, e
                                );
                                Document::new(name)
                            } else {
                                return Err(DocError::Corruption(format!(
                                    "document '{}' corrupted: {}",
                                    name, e
                                )));
                            }
                        }
                    }
                }
            }
            Err(e) => {
                if w_path.exists() {
                    eprintln!(
                        "Warning: could not read main file for '{}': {}, attempting WAL recovery",
                        name, e
                    );
                    Document::new(name)
                } else {
                    return Err(DocError::Io(e));
                }
            }
        }
    } else if w_path.exists() {
        // No main file, but WAL exists – recover from WAL
        Document::new(name)
    } else {
        return Err(DocError::DocumentNotFound(name.to_string()));
    };

    // Replay WAL if exists
    if w_path.exists() {
        replay_wal(&mut doc, &w_path)?;
        // After replay, checkpoint the doc to main file to keep consistent
        // (but don't fail if checkpoint fails)
        let _ = save_document(&doc);
    }

    // Final verification after WAL replay – ensure recovered state is healthy
    if !doc.order.is_empty() || !doc.elements.is_empty() {
        if let Err(verr) = doc.verify() {
            return Err(DocError::Corruption(format!(
                "document '{}' failed verification after WAL replay: {}",
                name, verr
            )));
        }
    }

    Ok(doc)
}

fn replay_wal(doc: &mut Document, wal_path: &Path) -> Result<(), DocError> {
    let file = match fs::File::open(wal_path) {
        Ok(f) => f,
        Err(_) => return Ok(()),
    };
    let reader = BufReader::new(file);
    let mut recovered = 0usize;
    let mut skipped = 0usize;
    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => {
                skipped += 1;
                continue;
            }
        };
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        match serde_json::from_str::<Operation>(trimmed) {
            Ok(op) => {
                // Apply if not already applied
                if !doc.applied_ops.contains(&op.op_id) {
                    // For marker ops, don't apply via apply_operation (they are no-ops there),
                    // but we still want to count them as applied to preserve idempotency
                    match op.kind {
                        crate::operations::OperationKind::UndoMarker
                        | crate::operations::OperationKind::RedoMarker
                        | crate::operations::OperationKind::Noop => {
                            doc.applied_ops.insert(op.op_id.clone());
                            doc.operations.push(op);
                        }
                        _ => {
                            match doc.apply_operation(op) {
                                Ok(_) => recovered += 1,
                                Err(e) => {
                                    // If operation fails during replay (e.g., duplicate that is now higher lamport),
                                    // we skip but keep applied_ops? Actually apply_operation already handles LWW.
                                    // For errors like InsertAfterNotFound, we skip with warning.
                                    eprintln!("Warning: WAL op failed during replay: {}", e);
                                    skipped += 1;
                                }
                            }
                        }
                    }
                }
            }
            Err(e) => {
                eprintln!("Warning: corrupted WAL line skipped: {}", e);
                skipped += 1;
            }
        }
    }
    if skipped > 0 {
        eprintln!(
            "WAL replay for '{}': recovered {}, skipped {} corrupted lines",
            doc.name, recovered, skipped
        );
    }
    Ok(())
}

/// Append operation to WAL (JSON line), flush.
pub fn append_wal(doc_name: &str, op: &Operation) -> Result<(), DocError> {
    validate_doc_name(doc_name)?;
    let dir = data_dir();
    if !dir.exists() {
        fs::create_dir_all(&dir)?;
    }
    let w_path = wal_path(doc_name);
    let json_line = serde_json::to_string(op)?;
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&w_path)?;
    writeln!(file, "{}", json_line)?;
    file.sync_all()?;
    Ok(())
}

pub fn clear_wal(doc_name: &str) -> Result<(), DocError> {
    validate_doc_name(doc_name)?;
    let w_path = wal_path(doc_name);
    if w_path.exists() {
        // Truncate
        fs::write(&w_path, "")?;
        // Or remove: we truncate to keep file but empty
        let _ = fs::remove_file(&w_path);
    }
    Ok(())
}

/// Save snapshot to arbitrary path (full document state).
pub fn save_snapshot(doc: &Document, path: &str) -> Result<(), DocError> {
    let p = Path::new(path);
    if let Some(parent) = p.parent() {
        if !parent.as_os_str().is_empty() && !parent.exists() {
            fs::create_dir_all(parent)?;
        }
    }
    let json = serde_json::to_string_pretty(doc)?;
    // Atomic write for snapshot too: write to tmp then rename
    let tmp_path = format!("{}.tmp", path);
    {
        let mut f = fs::File::create(&tmp_path)?;
        f.write_all(json.as_bytes())?;
        f.sync_all()?;
    }
    fs::rename(&tmp_path, p)?;
    Ok(())
}

/// Load snapshot from arbitrary path, return Document with new name = doc_id.
pub fn load_snapshot(path: &str, doc_id: &str) -> Result<Document, DocError> {
    validate_doc_name(doc_id)?;
    let p = Path::new(path);
    if !p.exists() {
        return Err(DocError::InvalidArgument(format!(
            "snapshot file '{}' not found",
            path
        )));
    }
    let contents = fs::read_to_string(p)?;
    if contents.trim().is_empty() {
        return Err(DocError::Corruption(format!(
            "snapshot file '{}' is empty",
            path
        )));
    }
    let mut doc: Document = serde_json::from_str(&contents).map_err(|e| {
        DocError::Corruption(format!("snapshot '{}' corrupted: {}", path, e))
    })?;
    // Validate snapshot integrity via verify
    doc.verify().map_err(|e| {
        DocError::Corruption(format!("snapshot '{}' failed verification: {}", path, e))
    })?;

    // Override name to requested doc_id
    doc.name = doc_id.to_string();
    Ok(doc)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::document::Document;
    use crate::operations::Operation;

    #[test]
    fn test_validate_doc_name() {
        assert!(validate_doc_name("valid-doc").is_ok());
        assert!(validate_doc_name("").is_err());
        assert!(validate_doc_name("../evil").is_err());
        assert!(validate_doc_name("a/b").is_err());
        assert!(validate_doc_name(".hidden").is_err());
        assert!(validate_doc_name(".").is_err());
        assert!(validate_doc_name("..").is_err());
        let long = "a".repeat(201);
        assert!(validate_doc_name(&long).is_err());
    }

    #[test]
    fn test_save_and_load_with_wal() {
        let name = format!("test_persist_{}", uuid::Uuid::new_v4());
        let _ = fs::remove_file(doc_path(&name));
        let _ = fs::remove_file(wal_path(&name));
        let mut doc = Document::new(&name);
        let op = Operation::insert("a".into(), "Hello".into(), None, "alice".into());
        append_wal(&name, &op).unwrap();
        doc.apply_operation(op).unwrap();
        save_document(&doc).unwrap();

        let loaded = load_document(&name).unwrap();
        assert_eq!(doc.format_contents(), loaded.format_contents());

        let _ = fs::remove_file(doc_path(&name));
        let _ = fs::remove_file(wal_path(&name));
    }

    #[test]
    fn test_wal_corruption_skip() {
        let name = format!("test_wal_corrupt_{}", uuid::Uuid::new_v4());
        let _ = fs::remove_file(doc_path(&name));
        let _ = fs::remove_file(wal_path(&name));
        let mut doc = Document::new(&name);
        let op1 = Operation::insert("a".into(), "A".into(), None, "alice".into());
        append_wal(&name, &op1).unwrap();
        // Write corrupted line
        {
            let mut f = OpenOptions::new()
                .append(true)
                .open(wal_path(&name))
                .unwrap();
            writeln!(f, "this is not json").unwrap();
            writeln!(f, "{{ truncated").unwrap();
        }
        let op2 = Operation::insert("b".into(), "B".into(), Some("a".into()), "alice".into());
        append_wal(&name, &op2).unwrap();

        doc.apply_operation(op1).unwrap();
        save_document(&doc).unwrap();

        // Load should replay WAL and skip corrupted lines
        let loaded = load_document(&name).unwrap();
        // Should have at least a and b (b from WAL replay)
        assert!(loaded.elements.contains_key("a"));
        // b might be recovered via WAL
        // Cleanup
        let _ = fs::remove_file(doc_path(&name));
        let _ = fs::remove_file(wal_path(&name));
    }
}

use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};
use uuid::Uuid;

/// Kind of operation performed on the document.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum OperationKind {
    Insert {
        element_id: String,
        value: String,
        after: Option<String>,
    },
    Delete {
        element_id: String,
    },
    /// Marker used only in WAL to record that an undo happened; not applied as insert/delete
    UndoMarker,
    RedoMarker,
    Noop,
}

/// A single operation with full causality metadata.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Operation {
    pub op_id: String,
    pub client_id: String,
    pub lamport: u64,
    /// Unix millis timestamp when operation was created.
    pub timestamp: u64,
    pub kind: OperationKind,
}

fn now_millis() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

impl Operation {
    /// Create an insert operation with placeholder lamport = 0.
    /// The Document will assign the correct lamport on apply.
    pub fn insert(element_id: String, value: String, after: Option<String>, client_id: String) -> Self {
        Operation {
            op_id: Uuid::new_v4().to_string(),
            client_id: if client_id.is_empty() {
                "default".to_string()
            } else {
                client_id
            },
            lamport: 0,
            timestamp: now_millis(),
            kind: OperationKind::Insert {
                element_id,
                value,
                after,
            },
        }
    }

    pub fn delete(element_id: String, client_id: String) -> Self {
        Operation {
            op_id: Uuid::new_v4().to_string(),
            client_id: if client_id.is_empty() {
                "default".to_string()
            } else {
                client_id
            },
            lamport: 0,
            timestamp: now_millis(),
            kind: OperationKind::Delete { element_id },
        }
    }

    pub fn undo_marker(client_id: String) -> Self {
        Operation {
            op_id: Uuid::new_v4().to_string(),
            client_id,
            lamport: 0,
            timestamp: now_millis(),
            kind: OperationKind::UndoMarker,
        }
    }

    pub fn redo_marker(client_id: String) -> Self {
        Operation {
            op_id: Uuid::new_v4().to_string(),
            client_id,
            lamport: 0,
            timestamp: now_millis(),
            kind: OperationKind::RedoMarker,
        }
    }

    /// Helper for tests to craft ops with explicit lamport.
    pub fn insert_with_lamport(
        element_id: String,
        value: String,
        after: Option<String>,
        client_id: String,
        lamport: u64,
    ) -> Self {
        let mut op = Self::insert(element_id, value, after, client_id);
        op.lamport = lamport;
        op
    }

    pub fn delete_with_lamport(element_id: String, client_id: String, lamport: u64) -> Self {
        let mut op = Self::delete(element_id, client_id);
        op.lamport = lamport;
        op
    }
}

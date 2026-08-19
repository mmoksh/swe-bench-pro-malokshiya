mod document;
mod error;
mod operations;
mod persistence;

use clap::{Parser, Subcommand};
use std::process;

#[derive(Parser)]
#[command(name = "collab-doc")]
#[command(about = "A persistent collaborative document engine with CRDT support")]
#[command(arg_required_else_help = true)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Create a new empty document
    New {
        document: String,
    },

    /// Insert an element into a document
    Insert {
        document: String,
        #[arg(long)]
        id: String,
        #[arg(long, allow_hyphen_values = true)]
        value: String,
        #[arg(long, allow_hyphen_values = true)]
        after: Option<String>,
        #[arg(long)]
        client: Option<String>,
    },

    /// Delete an element from a document
    Delete {
        document: String,
        #[arg(long)]
        id: String,
        #[arg(long)]
        client: Option<String>,
    },

    /// Retrieve an element by ID
    Get {
        document: String,
        #[arg(long)]
        id: String,
        #[arg(long)]
        client: Option<String>,
    },

    /// Print the complete document in logical order
    Format {
        document: String,
        #[arg(long)]
        client: Option<String>,
    },

    /// Report basic document state
    Status {
        document: String,
    },
}


fn run() -> Result<(), error::DocError> {
    let cli = Cli::parse();

    match cli.command {
        Commands::New { document } => {
            persistence::validate_doc_name(&document)?;
            if persistence::doc_exists(&document) {
                return Err(error::DocError::DocumentAlreadyExists(document));
            }
            let doc = document::Document::new(&document);
            persistence::save_document(&doc)?;
            // Ensure WAL is clean on new
            let _ = persistence::clear_wal(&document);
            Ok(())
        }
        Commands::Insert {
            document: doc_name,
            id,
            value,
            after,
            client,
        } => {
            persistence::validate_doc_name(&doc_name)?;
            if id.is_empty() {
                return Err(error::DocError::InvalidArgument(
                    "element ID cannot be empty".to_string(),
                ));
            }
            if value.len() > 10 * 1024 * 1024 {
                return Err(error::DocError::InvalidArgument(
                    "value too large (max 10MB)".to_string(),
                ));
            }
            let mut doc = persistence::load_document(&doc_name)?;
            let client_id = client.unwrap_or_else(|| "default".to_string());
            // Normalize empty after to None for ergonomics
            let normalized_after = match after {
                Some(s) if s.is_empty() => None,
                other => other.clone(),
            };
            let op =
                operations::Operation::insert(id.clone(), value, normalized_after, client_id);
            doc.apply_operation(op)?;
            // WAL: save final operation with assigned lamport
            if let Some(final_op) = doc.operations.last() {
                persistence::append_wal(&doc_name, final_op)?;
            }
            persistence::save_document(&doc)?;
            Ok(())
        }
        Commands::Delete {
            document: doc_name,
            id,
            client,
        } => {
            persistence::validate_doc_name(&doc_name)?;
            if id.is_empty() {
                return Err(error::DocError::InvalidArgument(
                    "element ID cannot be empty".to_string(),
                ));
            }
            let mut doc = persistence::load_document(&doc_name)?;
            let client_id = client.unwrap_or_else(|| "default".to_string());
            let op = operations::Operation::delete(id.clone(), client_id);
            doc.apply_operation(op)?;
            if let Some(final_op) = doc.operations.last() {
                persistence::append_wal(&doc_name, final_op)?;
            }
            persistence::save_document(&doc)?;
            Ok(())
        }
        Commands::Get {
            document: doc_name,
            id,
            client: _,
        } => {
            persistence::validate_doc_name(&doc_name)?;
            let doc = persistence::load_document(&doc_name)?;
            let value = doc.get_element(&id)?;
            println!("{}", value);
            Ok(())
        }
        Commands::Format {
            document: doc_name,
            client: _,
        } => {
            persistence::validate_doc_name(&doc_name)?;
            let doc = persistence::load_document(&doc_name)?;
            let contents = doc.format_contents();
            if !contents.is_empty() {
                print!("{}", contents);
            }
            Ok(())
        }
        Commands::Status { document: doc_name } => {
            persistence::validate_doc_name(&doc_name)?;
            let doc = persistence::load_document(&doc_name)?;
            let (elements, ops) = doc.status();
            println!("elements: {}", elements);
            println!("operations: {}", ops);
            let clients = doc.clients_list();
            if clients.is_empty() {
                println!("clients: 0");
            } else {
                // Print as comma-separated list for richer info, also parsers often look for word "clients"
                println!("clients: {}", clients.join(","));
            }
            println!("tombstones: {}", doc.tombstone_count());
            // Extra verification hint
            Ok(())
        }    }
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Error: {}", e);
        process::exit(1);
    }
}

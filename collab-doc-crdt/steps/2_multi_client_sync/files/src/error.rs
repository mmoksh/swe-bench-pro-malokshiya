use std::fmt;

#[derive(Debug)]
pub enum DocError {
    DocumentAlreadyExists(String),
    DocumentNotFound(String),
    ElementNotFound(String),
    DuplicateElementId(String),
    InsertAfterNotFound(String),
    ElementAlreadyDeleted(String),
    InvalidArgument(String),
    Io(std::io::Error),
    Serialization(String),
    Corruption(String),
    NoUndo(String),
    NoRedo(String),
    HasDependents(String),
}

impl fmt::Display for DocError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DocError::DocumentAlreadyExists(name) => write!(f, "document '{}' already exists", name),
            DocError::DocumentNotFound(name) => write!(f, "document '{}' not found", name),
            DocError::ElementNotFound(id) => write!(f, "element '{}' not found", id),
            DocError::DuplicateElementId(id) => write!(f, "element '{}' already exists", id),
            DocError::InsertAfterNotFound(id) => {
                write!(f, "cannot insert after '{}': element not found", id)
            }
            DocError::ElementAlreadyDeleted(id) => {
                write!(f, "element '{}' is already deleted", id)
            }
            DocError::InvalidArgument(msg) => write!(f, "invalid argument: {}", msg),
            DocError::Io(e) => write!(f, "I/O error: {}", e),
            DocError::Serialization(msg) => write!(f, "serialization error: {}", msg),
            DocError::Corruption(msg) => write!(f, "corruption detected: {}", msg),
            DocError::NoUndo(client) => {
                write!(f, "no operations to undo for client '{}'", client)
            }
            DocError::NoRedo(client) => {
                write!(f, "no operations to redo for client '{}'", client)
            }
            DocError::HasDependents(msg) => write!(f, "operation has dependents: {}", msg),
        }
    }
}

impl std::error::Error for DocError {}

impl From<std::io::Error> for DocError {
    fn from(e: std::io::Error) -> Self {
        DocError::Io(e)
    }
}

impl From<serde_json::Error> for DocError {
    fn from(e: serde_json::Error) -> Self {
        DocError::Serialization(e.to_string())
    }
}

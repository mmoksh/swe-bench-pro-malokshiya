# Milestone 1 — Build the Core Document Engine

Build a new **Rust** command-line application that manages persistent documents.

The application must be implemented from scratch in the current working directory. There is no existing application code to extend. You are responsible for creating the Rust project, implementing the document engine, implementing the command-line interface, and adding tests.

The final application will be evaluated primarily through black-box tests that invoke the CLI as a subprocess. Therefore, the command-line interface described below is a required public contract. Do not change command names, required arguments, or output formats.

## 1. Create the Rust Project

Create a standard Rust project that can be built and executed with Cargo.

The resulting project must build successfully with:

```text
cargo build
```

and the application must be runnable as:

```text
cargo run -- <command> ...
```

The project should also produce a CLI binary named:

```text
collab-doc
```

The implementation may use any reasonable Rust dependencies available in the environment.

Choose the internal architecture, data structures, persistence mechanism, and serialization format yourself.

## 2. Document Model

Implement a persistent ordered document containing logical elements.

Each element must have a unique stable identifier.

The document must support:

* creating a document;
* inserting elements;
* deleting elements;
* retrieving elements;
* formatting the complete document;
* reporting document status.

Represent modifications as explicit operations internally.

The implementation must be deterministic: given the same document state and sequence of operations, the resulting state must be identical.

Element identifiers must remain stable when other elements are inserted or deleted.

## 3. CLI Contract

The application must expose the following commands.

### `new`

Create a new empty document.

```text
collab-doc new <document>
```

Example:

```text
collab-doc new notes
```

The command must create persistent state for the document.

If the document already exists, return a non-zero exit code and an error message.

### `insert`

Insert an element into a document.

```text
collab-doc insert <document> --id <id> --value <value> [--after <element-id>]
```

Examples:

```text
collab-doc insert notes --id a --value "Hello"
collab-doc insert notes --id b --value "world" --after a
```

If `--after` is omitted, insert the element at the beginning of the document.

The supplied element ID must be unique within the document.

Inserting an element must not change the IDs of existing elements.

### `delete`

Delete an element.

```text
collab-doc delete <document> --id <id>
```

Example:

```text
collab-doc delete notes --id a
```

Deleting an element must not change the IDs of remaining elements.

Deleting an unknown element must produce a non-zero exit code.

### `get`

Retrieve an element by ID.

```text
collab-doc get <document> --id <id>
```

The command must print the element's value to stdout.

If the element does not exist, return a non-zero exit code.

### `format`

Print the complete document in logical order.

```text
collab-doc format <document>
```

For a document containing:

```text
a = Hello
b = world
c = !
```

the command should print:

```text
Hello
world
!
```

Each logical element should appear on its own line.

An empty document should produce an empty stdout result and a successful exit code.

### `status`

Report basic document state.

```text
collab-doc status <document>
```

The output must contain, at minimum:

```text
elements: <number>
```

and

```text
operations: <number>
```

Use exactly these field names so that automated tests can inspect the output.

Additional status information is allowed.

## 4. Persistence

Documents must persist across separate CLI invocations.

For example:

```text
collab-doc new notes
collab-doc insert notes --id a --value "Hello"
collab-doc insert notes --id b --value "world" --after a
collab-doc format notes
```

The final command must still be able to access the state created by the earlier commands.

The application must not rely on process-local memory for document state.

Choose an appropriate on-disk representation.

Persistence must preserve:

* element identifiers;
* element values;
* ordering;
* deletion state;
* operation information needed by the application.

## 5. Operation Semantics

Represent document modifications as operations.

At minimum, support operations corresponding to insertion and deletion.

Each operation must have a unique identifier.

The implementation should ensure that applying the same operation more than once does not corrupt document state.

Consider edge cases including:

* duplicate element IDs;
* deleting an unknown element;
* inserting after an unknown element;
* repeated deletion;
* empty values;
* special characters in values;
* documents containing many elements.

Choose sensible behavior for invalid operations and return non-zero exit codes rather than silently corrupting state.

## 6. Testing

Create a comprehensive automated test suite.

Tests should cover both the internal implementation and the CLI.

At minimum, verify:

* creating documents;
* inserting elements;
* inserting at the beginning;
* inserting after another element;
* deleting elements;
* retrieving elements;
* formatting documents;
* status reporting;
* persistence across separate processes;
* duplicate IDs;
* invalid element IDs;
* invalid document names;
* empty documents;
* multiple operations;
* large documents.

Also test combinations of operations rather than only isolated commands.

For example:

```text
new
→ insert
→ insert
→ delete
→ insert
→ get
→ format
→ status
```

The resulting state must be consistent across all commands.

## 7. Randomized Testing

Where useful, create randomized tests that generate sequences of document operations.

After each sequence, verify basic invariants such as:

* all live element IDs are unique;
* ordering is consistent;
* deleted elements are not returned by `get`;
* `format` reflects the logical ordering;
* `status` reports the correct number of live elements;
* restarting the CLI does not change document state.

If a randomized test discovers a failure, reduce it to a reproducible case, fix the underlying issue, and add a regression test.

## 8. Error Handling

The CLI must use exit codes consistently.

Successful commands must return exit code `0`.

Invalid operations must return a non-zero exit code.

Errors should be written to stderr rather than stdout.

Do not allow malformed input or invalid commands to corrupt existing documents.

The application should fail gracefully rather than panic for expected user errors.

## 9. Performance

The implementation should support documents containing at least 100,000 elements.

Create benchmarks or other measurements for:

* inserting many elements;
* formatting a large document;
* loading a large document;
* repeated lookups.

Avoid an obviously pathological implementation that reconstructs the entire persistent document unnecessarily for every operation.

Correctness is more important than aggressive optimization at this stage.

## 10. Completion Criteria

The milestone is complete only when:

1. A Rust project exists and builds successfully with Cargo.
2. The `collab-doc` binary is produced.
3. All six required CLI commands are implemented:

   * `new`
   * `insert`
   * `delete`
   * `get`
   * `format`
   * `status`
4. The CLI arguments and flags match the contract above.
5. Document state persists across independent CLI invocations.
6. Document operations behave deterministically.
7. Element identifiers remain stable.
8. Invalid operations return non-zero exit codes.
9. The automated test suite passes.
10. CLI behavior is covered by black-box tests.
11. Large documents can be handled successfully.
12. No required functionality remains a stub or placeholder.

Before finishing, run:

```text
cargo build
cargo test
```

and exercise the CLI through separate process invocations.

The final repository and executable behavior are the primary deliverables.

Provide a concise final report describing what you implemented, the tests you ran, and any remaining limitations.

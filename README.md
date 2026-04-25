# tgenfmt

Conservative formatter for LLVM TableGen files.

The formatter is intentionally small today. It is designed to be usable in
`pre-commit` while the parser and pretty-printer grow toward the MLIR style
captured in `MLIR_TABLEGEN_STYLE.md`.

## Usage

Format files in place:

```bash
tgenfmt path/to/file.td
```

Check without writing:

```bash
tgenfmt --check path/to/file.td
```

Override the soft line-width target:

```bash
tgenfmt --line-width 100 path/to/file.td
```

## Pre-commit

Use this repository as a pre-commit hook:

```yaml
repos:
-   repo: https://github.com/your-org/tgenfmt
    rev: v0.1.0
    hooks:
    -   id: tgenfmt
```

For local development:

```yaml
repos:
-   repo: local
    hooks:
    -   id: tgenfmt
        name: Format LLVM TableGen files
        entry: tgenfmt
        language: python
        files: \.td$
```

## Current Behavior

- Normalizes simple `include` and `foreach` spacing.
- Expands long one-line `let arguments = (ins ...)` and
  `let results = (outs ...)` DAGs.
- Wraps long ODS op headers with final trait lists.
- Preserves existing `let` and `defvar` alignment.
- Ensures a final newline for non-empty files.
- Preserves `[{ ... }]` blocks as opaque text.
- Supports `// tgenfmt: off` and `// tgenfmt: on`.

## License

Apache License 2.0. The canonical license text is included in `LICENSE`.

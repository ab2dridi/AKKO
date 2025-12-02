## Context

JSON serialization is a critical operation in AKKO, especially for encrypting and storing credentials. Python's built-in `json` module is slower and less efficient for our needs.

## Decision

We chose `orjson` for JSON serialization because:
- It is significantly faster than `json` and `ujson`.
- It supports strict typing and integrates well with Pydantic.
- It provides advanced options like `OPT_INDENT_2` for pretty-printing.

## Consequences

- All JSON operations must use `orjson.dumps` and `orjson.loads`.
- Contributors must ensure compatibility with `orjson`.

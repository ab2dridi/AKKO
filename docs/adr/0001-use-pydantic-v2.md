# ADR 0001: Use Pydantic v2

## Context

Pydantic is used for data validation and serialization in AKKO. The release of Pydantic v2 introduced significant improvements, including better performance and a cleaner API.

## Decision

We chose Pydantic v2 for the following reasons:
- Improved performance for large datasets.
- Cleaner API with `model_validate` and `model_dump`.
- Better support for strict typing and mypy integration.

## Consequences

- All models must use the v2 API (e.g., `model_validate` instead of `parse_obj`).
- Contributors must ensure compatibility with Pydantic v2.

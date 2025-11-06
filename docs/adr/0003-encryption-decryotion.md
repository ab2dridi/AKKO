## Context

AKKO encrypts credentials locally to ensure data privacy and security. The encryption process must be robust and easy to use.

## Decision

We use `cryptography.Fernet` for encryption and decryption because:
- It provides authenticated encryption with AES-128 in CBC mode.
- It is simple to implement and widely supported.

## Consequences

- All encryption keys are derived using `derive_key` from the master password.
- Contributors must avoid logging or exposing secrets in plain text.

# Security and Trust Model

This bot handles private documents, so the product promise must be concrete and verifiable:

> Your documents are isolated to your Telegram account, embedded locally, and deletable by you. To answer a question, only the relevant extracted text fragments are sent to the configured LLM provider.

## Current Controls

- Per-user isolation: all document retrieval and list operations filter by Telegram `user_id`.
- Local embeddings: document chunks are embedded on the bot host with `fastembed`; no embedding API receives document text.
- Limited LLM disclosure: answer generation sends the user question plus the top retrieved chunks, not every uploaded file.
- Deletion controls: users can delete one document from `/list` or remove all account data with `/reset`.
- Upload limits: file size, document count, chunk count, and DOCX uncompressed size are capped.
- Temporary upload cleanup: downloaded files are removed after parsing.
- Cited answers: the prompt requires inline source citations and refuses unsupported answers.

## User-Facing Disclosure

Use `/privacy` and the BotFather description to state the data flow plainly:

- Stored locally: extracted text, filenames, embeddings, upload metadata, and locale.
- Sent externally: question and selected document fragments for answer generation.
- Not sent externally for embeddings: full document text is not sent to an embedding API.
- User control: `/list` deletes one document; `/reset` deletes all documents and chunks for the Telegram account.

## Production Hardening Roadmap

These items are recommended before asking users to trust the bot with highly sensitive documents:

1. Encrypt the SQLite database or move to encrypted managed storage with locked-down backups.
2. Add an explicit retention policy, for example auto-delete documents after 7 or 30 days.
3. Add a provider privacy mode toggle or a self-hosted LLM option for users who cannot send fragments to external providers.
4. Add admin-free data export/deletion audit logs without storing document contents in logs.
5. Add per-user quotas and abuse throttling for uploads and questions.
6. Add deployment controls: secret rotation, restricted filesystem permissions, host disk encryption, and private network access.
7. Add integration tests for cross-user isolation and deletion behavior.

## Non-Claims

Do not claim end-to-end encryption or zero external processing in marketing copy unless the architecture changes. Telegram, the bot host, and the configured LLM provider remain part of the trust boundary.

# Review notes

This folder was reconstructed from the uploaded pasted-code document, not from a verified Git repository.

## Important limitations found during extraction
- Several Python code blocks in the source text have malformed indentation or missing lines because of formatting in the pasted document.
- The pasted document references files that are not included as code blocks, including `app/main.py`, `app/workers/outbox_worker.py`, and `docs/architecture.md`.
- Terraform, Grafana dashboards, and load-test scripts were explicitly omitted in the source document.
- The pasted code has not been run against PostgreSQL/Redis and should not be treated as production-ready.

## Next steps
1. Open this folder in VS Code.
2. Review `REVIEW_NOTES.md`.
3. Fix syntax/import errors before running Docker or tests.
4. Use `.env.example` only for local development; replace all example secrets before deployment.

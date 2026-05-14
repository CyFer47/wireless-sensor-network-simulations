# Local DB Config

- Keep `.env` local only.
- Never upload `.env` to GitHub or copy it into any export folder.
- `.env.example` is safe to commit and share.
- Use `--import-db` only after the database connection has been tested locally.
- If `.env` still contains `CHANGE_ME_LOCAL_ONLY`, the import wrapper will fail with a clear error.

# GitHub Commands

## Inspect repository state
```bash
cd /home/cyfer/FYP/WSN_simulation
git status
git remote -v
git log --oneline -5
```

## Safe sync flow
```bash
git pull --rebase
git add <safe-files-only>
git commit -m "Update final demo workspace and command guides"
git push origin main
```

## Safety check before adding files
```bash
find . -name ".env" -o -name "*.sql" -o -name "*.db" -o -name "*.log" -o -name "*.tar.gz" -o -name ".venv"
```

## Rules
- Do not push `.env`, `.venv`, database dumps, logs, or heavy output folders.
- Keep the commit small and documentation-focused.
- If the remote has advanced, rebase instead of forcing a push.

# Dashboard Commands

## Discover the dashboard folder
```bash
find /home/cyfer/FYP -maxdepth 5 \( -name "package.json" -o -name "manage.py" -o -name "app.py" -o -name "server.js" \) -print
```

No `package.json` was found in the inspected workspace. The dashboard entry point is the FastAPI backend in the web-monitor folder.

## Start the backend dashboard
```bash
cd "/home/cyfer/FYP/garbage/WSN Dashboard Milestone V2/web-monitor/backend"
cp config/.env.example config/.env
python3 -m pip install --break-system-packages -r requirements.txt
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8083
```

## Open the UI
- `http://127.0.0.1:8083/`
- `http://127.0.0.1:8083/docs`
- If you need a standalone static frontend:
```bash
cd "/home/cyfer/FYP/garbage/WSN Dashboard Milestone V2/web-monitor/frontend"
cp config.example.js config.js
python3 -m http.server 5174
```

## Demo note
For viva purposes, use the backend-served UI because it is the simplest and most reliable live path.

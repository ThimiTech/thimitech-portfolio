#!/usr/bin/env bash
# Thimi Tech OS - one-click dev launcher for Linux/macOS.
# Run:  ./start-dev.sh   (first time: chmod +x start-dev.sh)   - Ctrl+C stops everything it started.
set -eo pipefail
cd "$(dirname "$0")"
ROOT=$PWD

echo
echo "  =============================================="
echo "    Thimi Tech OS - starting backend + frontend"
echo "  =============================================="
echo

PIDS=()
cleanup() {
  for pid in "${PIDS[@]}"; do
    pkill -TERM -P "$pid" 2>/dev/null || true   # children (vite, celery pool)
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT
trap 'exit 130' INT TERM

port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
fail() { echo; echo "[error] $1"; exit 1; }

# ---------------- Backend setup ----------------
cd "$ROOT/backend"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[setup] Created backend/.env from .env.example - edit DB_* there if the database step fails."
fi

if [ ! -x .venv/bin/python ]; then
  echo "[setup] Creating Python virtual environment (needs Python 3.12+)..."
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.13 .venv
  else
    PYBIN=$(command -v python3.13 || command -v python3.12 || command -v python3) || fail "Python 3.12+ not found."
    "$PYBIN" -m venv .venv
  fi
fi
PY="$ROOT/backend/.venv/bin/python"

echo "[setup] Syncing Python packages..."
if command -v uv >/dev/null 2>&1; then
  uv pip install -q --python .venv -r requirements.txt
else
  "$PY" -m pip install -q -r requirements.txt
fi

set +e; "$PY" dev_check.py db; DBSTATE=$?; set -e
[ "$DBSTATE" -eq 1 ] && fail "Database check failed - see the message above."

echo "[setup] Applying database migrations..."
"$PY" manage.py migrate --noinput

if [ "$DBSTATE" -eq 3 ]; then
  echo "[setup] Fresh database - creating admin and loading demo data..."
  DJANGO_SUPERUSER_PASSWORD=admin12345 "$PY" manage.py createsuperuser --noinput \
    --username admin --email admin@thimitech.com || true
  "$PY" seed_dev.py
fi

# ---------------- Redis (Celery broker) ----------------
if command -v docker >/dev/null 2>&1; then
  docker start thimi-redis >/dev/null 2>&1 \
    || docker run -d --name thimi-redis --restart unless-stopped -p 6379:6379 redis:7-alpine >/dev/null 2>&1 \
    || true
fi
CELERY=0
"$PY" dev_check.py redis && CELERY=1
if [ "$CELERY" -eq 0 ]; then
  echo "[info] Redis not reachable - background jobs will run inline instead of in Celery."
  export CELERY_TASK_ALWAYS_EAGER=True
fi

# ---------------- Start backend + Celery ----------------
if port_busy 8000; then
  echo "[ok] Backend already running on :8000 - leaving it as is."
else
  "$PY" manage.py runserver 127.0.0.1:8000 & PIDS+=($!)
  if [ "$CELERY" -eq 1 ]; then
    "$PY" -m celery -A config worker -l info & PIDS+=($!)
    "$PY" -m celery -A config beat -l info & PIDS+=($!)
  fi
fi

# ---------------- Frontend ----------------
cd "$ROOT/frontend"
command -v npm >/dev/null 2>&1 || fail "Node.js / npm not found. Install Node 20.19+ and run again."
if [ ! -d node_modules ]; then
  echo "[setup] Installing frontend packages - first run only..."
  npm install
fi
if port_busy 5173; then
  echo "[ok] Frontend already running on :5173 - leaving it as is."
else
  npm run dev & PIDS+=($!)
fi

sleep 6
(xdg-open http://localhost:5173 || open http://localhost:5173) >/dev/null 2>&1 || true

cat <<'EOF'

  Website      http://localhost:5173
  Workspace    http://localhost:5173/app
  API docs     http://127.0.0.1:8000/api/docs/
  Django admin http://127.0.0.1:8000/admin/

  Admin login  admin@thimitech.com / admin12345
  Demo logins  hr@ / manager@ / sita@thimitech.com  -  password Thimi@12345

  Press Ctrl+C to stop everything this script started.
EOF

if [ ${#PIDS[@]} -gt 0 ]; then
  wait
else
  echo "[ok] Everything was already running; nothing to supervise."
  trap - EXIT
fi

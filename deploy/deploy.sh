#!/bin/bash
# Redeploy loop for the new voice diary (JEV). Run from anywhere.
#   bash ~/app/voicediary_jev/deploy/deploy.sh
set -euo pipefail
APP=/home/pmpmt/app/voicediary_jev
cd "$APP"

echo "== git pull =="
git pull --ff-only

echo "== python deps =="
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "== tailwind build =="
.venv/bin/python manage.py tailwind build

echo "== migrate =="
.venv/bin/python manage.py migrate --noinput

echo "== collectstatic =="
.venv/bin/python manage.py collectstatic --noinput

echo "== restart =="
sudo -n systemctl restart voicediary-web.service && echo "restarted voicediary-web" || echo "restart needs sudo (run: sudo systemctl restart voicediary-web)"

echo "== health =="
curl -s -o /dev/null -w "local /voice/ -> %{http_code}\n" \
  -H "Host: voice.utter-it.com" -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8001/voice/ || true

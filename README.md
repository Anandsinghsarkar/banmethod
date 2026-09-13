# CaseDesk — Complaint Case Manager

A small Flask + SQLite app for manually organizing complaint cases and preparing a text draft for submission through a platform's official process. It does **not** send reports, contact platforms, scrape accounts, or automate bans/enforcement.

## Features

- Password-protected single-admin login
- Add, search, and filter cases
- Categories and status tracking
- Optional public reference URL
- Export a plain-text complaint draft
- SQLite persistence, CSRF protection, and bounded input sizes

## Run locally / Termux

Python 3.10+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD='choose-a-strong-password'
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_PATH="$PWD/cases.db"
gunicorn --bind 127.0.0.1:5000 main:app
```

Open <http://127.0.0.1:5000>. Do not expose the development app publicly without HTTPS, a strong secret, secure deployment configuration, and persistent storage. Set `ADMIN_PASSWORD` and `SECRET_KEY` in your hosting provider's environment settings; never commit real secrets.

## Render

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn --bind 0.0.0.0:$PORT main:app`
- Set `ADMIN_PASSWORD` and `SECRET_KEY` as environment variables.
- For persistent SQLite data, attach a persistent disk and set `DATABASE_PATH` to a file path on that disk, for example `/var/data/cases.db`.

## Important

This is a basic private case tracker, not a legal service or a platform enforcement tool. Submit complaints yourself, truthfully, and only when appropriate. Avoid storing passwords, private messages, or unnecessary personal data in case notes.

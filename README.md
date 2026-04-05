# GitHub Repository Analyzer

Python 3 desktop app (Tkinter) that uses the **GitHub REST API** to inspect repositories you can access: commit history, contributors, charts, regex filters on messages, CSV/JSON/TXT exports, and a simple **conflict-risk** view based on overlapping file edits in recent commits (not real merge resolution).

## Features

- Local sign-up / login, passwords hashed (PBKDF2), SQLite storage  
- Save GitHub username + PAT, test connection, per-user storage  
- Repository list (search by name), analyze, favorites  
- Analysis: metrics, contributor and commit tables, matplotlib charts, regex presets  
- Exports under `exports/`  
- Favorites and analysis history with reopen (re-fetches from GitHub)

## Stack

Python 3, Tkinter, sqlite3, requests, matplotlib; `re`, csv, json, hashlib, datetime in the stdlib.

## Layout

```
github_repo_analyzer/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── database/     # app.db at runtime (gitignored)
├── exports/
├── models/
├── services/
├── data/
├── utils/
└── ui/
```

## Setup

```bash
cd github_repo_analyzer
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py
```

SQLite file: `database/app.db` (created on first run). Optional env: `DATABASE_PATH` to override the DB file location.

## GitHub token

GitHub → Settings → Developer settings → Personal access tokens (classic). For private repos use scope **`repo`**; public-only can use **`public_repo`**. Paste in **Connect GitHub** in the app (stored locally).

## Git

Initialize the repo **inside** this folder before pushing:

```bash
git init
git add .
git status
```

Do not commit `database/app.db` or `exports/` contents (see `.gitignore`).

## Limits

No automatic merge or push. Analysis is capped (e.g. ~400 commits; ~90 recent commits used for file-level conflict hints). Subject to GitHub API rate limits.

## Author

Add your name and module here.

# vscode-copilot

Inbox triage using the **GitHub Copilot model you already have in VS Code** as
the AI brain — no separate API key, no external service. The Copilot model is
reached through the VS Code Language Model API (`vscode.lm`), which is only
callable from inside a VS Code extension, so the "brain" lives as a small
extension here.

## Pieces

```
backend/     Python — Outlook COM fetch + Flask server for the dashboard
extension/   VS Code extension — the AI brain (calls the Copilot model)
dashboard/   The single-page dashboard (opens in any browser)
data/        emails.json (fetched mail) + results.json (enriched) — gitignored
```

## The flow

```
1. backend/fetch_outlook.py      Outlook ──COM──▶ data/emails.json
2. extension (run in VS Code)    emails.json ──Copilot──▶ data/results.json
3. backend/server.py             serves dashboard/ + results.json at :5000
4. browser                       open http://localhost:5000, click Refresh
```

The three pieces are decoupled — they talk through the two JSON files in
`data/`. That means you can test the fetch without the brain, the brain without
the dashboard, etc.

## One-time setup

**Python side**
```bash
cd backend
python -m pip install -r requirements.txt
```
(`pywin32` only installs on Windows — that's expected; the COM fetch is
Windows + desktop Outlook only.)

**Extension side**
```bash
cd extension
npm install
npm run compile
```

## Running it

1. **Fetch mail** (Windows, Outlook desktop open):
   ```bash
   cd backend && python fetch_outlook.py
   ```
   → writes `data/emails.json`.

2. **Run the brain**: open the `extension/` folder in VS Code, press **F5**
   (launches an Extension Development Host), then `Ctrl+Shift+P` →
   **"Inbox Triage: Enrich emails"**. Approve the Copilot consent prompt the
   first time. → writes `data/results.json`.

3. **Serve the dashboard**:
   ```bash
   cd backend && python server.py
   ```
   → open http://localhost:5000.

## Rules vs AI — how work is split

- **Bucketing** (Need reply / Urgent / Overdue / FYI / Automated) is done by
  **Python rules** in `backend/rules.py` — fast, offline, explainable, and it
  keeps mail content local. Edit the rules there (your senders, projects,
  ticket patterns).
- **Summaries, action points, suggested replies** are done by the **Copilot
  model** in the extension — but only for the emails that land in real buckets,
  not all of them.

## Compliance note

This uses your Copilot coding entitlement to process mailbox text. It works
technically, but confirm with HSBC IT/compliance that it's within
acceptable-use before running it on real mail day to day. Nothing leaves your
machine except the per-email text sent to the Copilot model via VS Code.

# inbox-triage

A personal inbox-triage dashboard: pull mail from Outlook, let an AI model
bucket and summarize it, and view the result as a single refreshable dashboard
in the browser.

This repo is organized by **the AI brain each approach uses**. Each top-level
folder is one self-contained implementation of the same idea — same dashboard,
same Outlook fetch, different "brain" doing the summarizing. Add a new folder
when you explore a new brain.

## Folders

| Folder | Brain | Status |
|--------|-------|--------|
| [`vscode-copilot/`](./vscode-copilot) | GitHub Copilot model via the VS Code Language Model API (no API key) | active |
| `azure-openai/` | Azure OpenAI endpoint + key | planned |
| `ollama/` | Local offline model (Llama 3 / Phi via Ollama) | planned |

## The shared idea

```
Outlook  ──(Python COM)──▶  emails.json
                                 │
                          AI brain (per folder)
                                 │
                          results.json
                                 │
                          Flask server  ──▶  dashboard in browser
```

The **fetch** (Python + Outlook COM) and the **dashboard** (HTML) stay the same
across approaches. Only the brain changes. Each folder has its own README with
run steps.

## Start here

See [`vscode-copilot/README.md`](./vscode-copilot/README.md) — the first working
approach, using the Copilot licence you already have in VS Code.

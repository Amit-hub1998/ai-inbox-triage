"""
Step 3: serve the dashboard and the triage data.

Routes:
  GET  /                -> the dashboard page
  GET  /api/results     -> current results.json (what the dashboard renders)
  POST /api/refresh     -> re-run the Outlook fetch, then return fresh data

Note on the AI step: the Copilot summaries are produced by the VS Code
extension, which writes data/results.json. This server does NOT call the model
(it can't — that only works inside VS Code). On refresh it re-fetches mail and
rebuilds buckets; it then merges in whatever AI summaries already exist in
results.json. If no AI summaries exist yet, it serves rule-based fallback
summaries so the dashboard is never empty.

Run:  python server.py   ->  http://localhost:5000
"""
import json
import os
import subprocess
import sys

from flask import Flask, jsonify, send_from_directory

BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "..", "data")
DASHBOARD_DIR = os.path.join(BASE, "..", "dashboard")
EMAILS_PATH = os.path.join(DATA_DIR, "emails.json")
RESULTS_PATH = os.path.join(DATA_DIR, "results.json")

app = Flask(__name__)


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fallback_summary(email):
    """A rule-based stand-in when the AI brain hasn't run for this email."""
    body = (email.get("body") or "").strip().replace("\n", " ")
    snippet = (body[:160] + "…") if len(body) > 160 else body
    return {
        "summary": snippet or email.get("subject", ""),
        "action": "Review (no AI summary yet — run the VS Code extension)",
        "priority": {"overdue": "High", "urgent": "High", "need": "Medium",
                     "fyi": "Low", "auto": "Routine"}.get(email.get("bucket"), "Medium"),
        "reply": "",
        "next_steps": [],
        "ai": False,
    }


def build_results():
    """
    Combine fetched emails (buckets) with AI enrichment (results.json), falling
    back to rule-based summaries where the AI hasn't run.
    """
    emails_doc = _load(EMAILS_PATH)
    if emails_doc is None:
        return {"error": "No emails.json yet. Run fetch_outlook.py first.",
                "total": 0, "counts": {}, "emails": []}

    ai_doc = _load(RESULTS_PATH) or {}
    ai_by_id = {e["id"]: e for e in ai_doc.get("emails", []) if e.get("id")}

    merged = []
    for e in emails_doc.get("emails", []):
        ai = ai_by_id.get(e.get("id"))
        enrichment = ai["enrichment"] if ai and ai.get("enrichment") else _fallback_summary(e)
        merged.append({**e, "enrichment": enrichment})

    return {
        "fetched_at": emails_doc.get("fetched_at"),
        "ai_run_at": ai_doc.get("generated_at"),
        "total": emails_doc.get("total", len(merged)),
        "counts": emails_doc.get("counts", {}),
        "emails": merged,
    }


@app.route("/")
def index():
    return send_from_directory(DASHBOARD_DIR, "index.html")


@app.route("/api/results")
def api_results():
    return jsonify(build_results())


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Re-run the Outlook fetch, then return fresh data."""
    try:
        subprocess.run([sys.executable, os.path.join(BASE, "fetch_outlook.py")],
                       check=True, cwd=BASE, timeout=120)
        status = "refreshed"
    except subprocess.CalledProcessError as exc:
        status = f"fetch-failed: {exc}"
    except FileNotFoundError:
        status = "fetch-missing"
    except subprocess.TimeoutExpired:
        status = "fetch-timeout"

    data = build_results()
    data["refresh_status"] = status
    return jsonify(data)


if __name__ == "__main__":
    print("Dashboard: http://localhost:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)

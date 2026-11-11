import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

// Shapes -------------------------------------------------------------------

interface Email {
  id: string;
  from: string;
  from_email?: string;
  subject: string;
  received?: string;
  body?: string;
  bucket: string;
  needs_ai?: boolean;
}

interface Enrichment {
  priority: "High" | "Medium" | "Low" | "Routine";
  summary: string;
  action: string;
  reply: string;
  next_steps: string[];
  ai: boolean;
}

// Paths: data/ sits two levels up from the compiled extension (out/)
function dataDir(): string {
  // extension/out/extension.js -> ../../data
  return path.resolve(__dirname, "..", "..", "data");
}

// The prompt --------------------------------------------------------------

function buildPrompt(email: Email): string {
  return [
    "You are an email triage assistant for a busy data analyst at a bank.",
    "Read the single email below and reply with ONLY a JSON object, no prose,",
    "no markdown fences, matching exactly this shape:",
    "{",
    '  "priority": "High" | "Medium" | "Low",',
    '  "summary": "one sentence, what this email is about",',
    '  "action": "the single most important action point for the reader",',
    '  "reply": "a one or two sentence suggested reply the reader could send",',
    '  "next_steps": ["short", "concrete", "steps"]',
    "}",
    "",
    `From: ${email.from} <${email.from_email ?? ""}>`,
    `Subject: ${email.subject}`,
    `Body: ${(email.body ?? "").slice(0, 1500)}`,
  ].join("\n");
}

function safeParse(raw: string): Partial<Enrichment> | null {
  // Model sometimes wraps JSON in ```json fences — strip them.
  const cleaned = raw.replace(/```json/gi, "").replace(/```/g, "").trim();
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start === -1 || end === -1) return null;
  try {
    return JSON.parse(cleaned.slice(start, end + 1));
  } catch {
    return null;
  }
}

// Core --------------------------------------------------------------------

async function enrichOne(
  model: vscode.LanguageModelChat,
  email: Email,
  token: vscode.CancellationToken
): Promise<Enrichment> {
  const messages = [vscode.LanguageModelChatMessage.User(buildPrompt(email))];
  const response = await model.sendRequest(messages, {}, token);

  let text = "";
  for await (const fragment of response.text) {
    text += fragment;
  }

  const parsed = safeParse(text);
  if (!parsed) {
    return {
      priority: "Medium",
      summary: email.subject,
      action: "Review — model returned unparseable output",
      reply: "",
      next_steps: [],
      ai: true,
    };
  }

  return {
    priority: (parsed.priority as Enrichment["priority"]) ?? "Medium",
    summary: parsed.summary ?? email.subject,
    action: parsed.action ?? "",
    reply: parsed.reply ?? "",
    next_steps: Array.isArray(parsed.next_steps) ? parsed.next_steps : [],
    ai: true,
  };
}

async function enrichAll(): Promise<void> {
  const emailsPath = path.join(dataDir(), "emails.json");
  const resultsPath = path.join(dataDir(), "results.json");

  if (!fs.existsSync(emailsPath)) {
    vscode.window.showErrorMessage(
      `No emails.json found at ${emailsPath}. Run fetch_outlook.py first.`
    );
    return;
  }

  // Pick the Copilot model you're already licensed for.
  const [model] = await vscode.lm.selectChatModels({ vendor: "copilot" });
  if (!model) {
    vscode.window.showErrorMessage(
      "No Copilot model available. Make sure GitHub Copilot is installed and signed in."
    );
    return;
  }

  const doc = JSON.parse(fs.readFileSync(emailsPath, "utf-8"));
  const emails: Email[] = doc.emails ?? [];
  const toProcess = emails.filter((e) => e.needs_ai);

  if (toProcess.length === 0) {
    vscode.window.showInformationMessage("No emails flagged for AI summary.");
    return;
  }

  const enriched: { id: string; enrichment: Enrichment }[] = [];

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Inbox Triage: summarizing with Copilot",
      cancellable: true,
    },
    async (progress, token) => {
      let done = 0;
      for (const email of toProcess) {
        if (token.isCancellationRequested) break;
        progress.report({
          message: `${done + 1}/${toProcess.length}: ${email.subject.slice(0, 40)}`,
          increment: 100 / toProcess.length,
        });
        try {
          const enrichment = await enrichOne(model, email, token);
          enriched.push({ id: email.id, enrichment });
        } catch (err) {
          enriched.push({
            id: email.id,
            enrichment: {
              priority: "Medium",
              summary: email.subject,
              action: `Error: ${err instanceof Error ? err.message : String(err)}`,
              reply: "",
              next_steps: [],
              ai: false,
            },
          });
        }
        done++;
      }
    }
  );

  const out = {
    generated_at: new Date().toISOString(),
    model: model.name,
    count: enriched.length,
    emails: enriched,
  };
  fs.writeFileSync(resultsPath, JSON.stringify(out, null, 2), "utf-8");

  vscode.window.showInformationMessage(
    `Enriched ${enriched.length} emails -> results.json. Refresh the dashboard.`
  );
}

// Activation --------------------------------------------------------------

export function activate(context: vscode.ExtensionContext) {
  const cmd = vscode.commands.registerCommand("inboxTriage.enrich", () => {
    enrichAll().catch((err) =>
      vscode.window.showErrorMessage(
        `Inbox Triage failed: ${err instanceof Error ? err.message : String(err)}`
      )
    );
  });
  context.subscriptions.push(cmd);
}

export function deactivate() {}

import { createServer } from "node:http";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import crypto from "node:crypto";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 8787);
const ANTHROPIC_VERSION = "2023-06-01";
const DEFAULT_MODEL = "claude-sonnet-4-6";

await loadDotEnv(path.join(__dirname, ".env"));

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8"
};

const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${req.headers.host}`);

    if (req.method === "GET" && url.pathname === "/api/scenarios") {
      const scenarios = await readJson(path.join(__dirname, "data", "scenarios.json"));
      return sendJson(res, 200, scenarios);
    }

    if (req.method === "POST" && url.pathname === "/api/run") {
      const body = await readRequestJson(req);
      const result = await runElicitationStage(body);
      await saveRunLog(body, result);
      return sendJson(res, 200, result);
    }

    if (req.method === "GET" && url.pathname === "/") {
      return sendFile(res, path.join(__dirname, "public", "index.html"));
    }

    if (req.method === "GET" && !url.pathname.includes("..")) {
      const filePath = path.join(__dirname, "public", url.pathname);
      return sendFile(res, filePath);
    }

    sendJson(res, 404, { error: "Not found" });
  } catch (error) {
    sendJson(res, 500, { error: error.message || String(error) });
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`ICPM elicitation prototype running at http://localhost:${PORT}`);
});

async function runElicitationStage(body) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add a fresh key.");
  }

  const model = body.model || process.env.ANTHROPIC_MODEL || DEFAULT_MODEL;
  const prompt = buildPrompt(body);

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": ANTHROPIC_VERSION
    },
    body: JSON.stringify({
      model,
      max_tokens: 4000,
      messages: [{ role: "user", content: prompt }]
    })
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error?.message || `Anthropic API error: ${response.status}`);
  }

  const text = payload.content?.map((item) => item.text || "").join("\n").trim() || "";
  return {
    id: crypto.randomUUID(),
    created_at: new Date().toISOString(),
    model,
    stage: body.stage,
    raw_text: text,
    parsed: parseJsonFromText(text)
  };
}

function buildPrompt(body) {
  const scenario = body.scenario || {};
  const stage = body.stage || "one_shot";
  const initial = scenario.initial_description || "";
  const answers = body.answers || "";
  const previous = body.previousOutput ? JSON.stringify(body.previousOutput, null, 2) : "";
  const questions = body.questions ? JSON.stringify(body.questions, null, 2) : "";

  const shared = `
You are supporting a process mining research prototype.
Use only the synthetic scenario information provided below.
Do not invent company-specific system names, product names, confidential logs, internal metrics, or real organizational details.
Return valid JSON only. Do not wrap it in Markdown.

Scenario ID: ${scenario.id || "unknown"}
Scenario title: ${scenario.title || "unknown"}
Initial workflow description:
${initial}
`;

  if (stage === "questions") {
    return `${shared}
Task: Detect missing or ambiguous process information required for automation opportunity assessment.

Return JSON with this shape:
{
  "missing_information": [
    {
      "category": "actor | system | input | output | decision | exception | dependency | frequency | manual_effort | data_availability | integration_constraint | risk_or_approval",
      "gap": "short description of the missing information",
      "why_it_matters": "why this gap affects workflow reconstruction or automation assessment"
    }
  ],
  "clarification_questions": [
    {
      "id": "Q1",
      "question": "targeted question for the domain expert",
      "targets": ["category or activity this question clarifies"]
    }
  ]
}
Limit the questions to 6 highly useful questions.`;
  }

  if (stage === "oracle_answers") {
    return `${shared}
Clarification question output:
${questions || previous}

Reference workflow for oracle use:
${JSON.stringify(scenario.reference_workflow || {}, null, 2)}

Task: Simulate a concise domain expert who answers only the clarification questions using the reference workflow.
Do not reveal the full reference workflow. Do not add details that are not needed by the questions.

Return JSON with this shape:
{
  "answers": [
    {
      "question_id": "Q1",
      "question": "original clarification question",
      "answer": "short answer grounded in the reference workflow"
    }
  ]
}`;
  }

  if (stage === "update") {
    return `${shared}
Previous intermediate output:
${previous}

Domain expert answers:
${answers}

Task: Incorporate the answers and produce an updated structured workflow representation plus automation opportunities.

Return JSON with this shape:
{
  "workflow": {
    "activities": [{"id": "A1", "name": "...", "actor": "...", "system": "...", "inputs": [], "outputs": []}],
    "decisions": [{"id": "D1", "condition": "...", "branches": []}],
    "exceptions": [],
    "dependencies": [{"from": "A1", "to": "A2", "type": "control_flow"}]
  },
  "automation_opportunities": [
    {"target": "activity or decision", "rationale": "...", "required_data": [], "constraints": [], "confidence": "low | medium | high"}
  ],
  "remaining_gaps": []
}`;
  }

  if (stage === "checklist") {
    return `${shared}
Task: Generate a structured workflow and automation opportunity assessment from the initial description only.
Use this fixed checklist internally: activities, actors, systems, inputs, outputs, decisions, exceptions, dependencies, frequency, manual effort, data availability, integration constraints, risk or approval constraints.
You cannot ask follow-up questions.

Return JSON with this shape:
{
  "workflow": {
    "activities": [{"id": "A1", "name": "...", "actor": "...", "system": "...", "inputs": [], "outputs": []}],
    "decisions": [{"id": "D1", "condition": "...", "branches": []}],
    "exceptions": [],
    "dependencies": [{"from": "A1", "to": "A2", "type": "control_flow"}]
  },
  "automation_opportunities": [
    {"target": "activity or decision", "rationale": "...", "required_data": [], "constraints": [], "confidence": "low | medium | high"}
  ],
  "assumptions": []
}`;
  }

  return `${shared}
Task: Generate a structured workflow and automation opportunity assessment from the initial description only.
You cannot ask follow-up questions and you do not have access to the reference workflow.

Return JSON with this shape:
{
  "workflow": {
    "activities": [{"id": "A1", "name": "...", "actor": "...", "system": "...", "inputs": [], "outputs": []}],
    "decisions": [{"id": "D1", "condition": "...", "branches": []}],
    "exceptions": [],
    "dependencies": [{"from": "A1", "to": "A2", "type": "control_flow"}]
  },
  "automation_opportunities": [
    {"target": "activity or decision", "rationale": "...", "required_data": [], "constraints": [], "confidence": "low | medium | high"}
  ],
  "assumptions": []
}`;
}

function parseJsonFromText(text) {
  try {
    return JSON.parse(text);
  } catch {
    const match = text.match(/\{[\s\S]*\}/);
    if (!match) return null;
    try {
      return JSON.parse(match[0]);
    } catch {
      return null;
    }
  }
}

async function saveRunLog(requestBody, result) {
  const runsDir = path.join(__dirname, "data", "runs");
  await mkdir(runsDir, { recursive: true });
  const scenarioId = requestBody.scenario?.id || "unknown";
  const safeStage = String(requestBody.stage || "run").replace(/[^a-z0-9_-]/gi, "_");
  const fileName = `${new Date().toISOString().replace(/[:.]/g, "-")}_${scenarioId}_${safeStage}.json`;
  await writeFile(path.join(runsDir, fileName), JSON.stringify({ request: requestBody, result }, null, 2));
}

async function sendFile(res, filePath) {
  if (!existsSync(filePath)) {
    return sendJson(res, 404, { error: "File not found" });
  }
  const ext = path.extname(filePath);
  const content = await readFile(filePath);
  res.writeHead(200, { "content-type": contentTypes[ext] || "application/octet-stream" });
  res.end(content);
}

async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, "utf8"));
}

async function readRequestJson(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

function sendJson(res, status, payload) {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload, null, 2));
}

async function loadDotEnv(filePath) {
  if (!existsSync(filePath)) return;
  const raw = await readFile(filePath, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const index = trimmed.indexOf("=");
    if (index === -1) continue;
    const key = trimmed.slice(0, index).trim();
    const value = trimmed.slice(index + 1).trim().replace(/^["']|["']$/g, "");
    if (!process.env[key]) process.env[key] = value;
  }
}

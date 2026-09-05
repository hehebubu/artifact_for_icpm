const scenarioSelect = document.querySelector("#scenarioSelect");
const scenarioDomain = document.querySelector("#scenarioDomain");
const scenarioId = document.querySelector("#scenarioId");
const initialDescription = document.querySelector("#initialDescription");
const referenceWorkflow = document.querySelector("#referenceWorkflow");
const output = document.querySelector("#output");
const answers = document.querySelector("#answers");
const statusEl = document.querySelector("#status");
const modelInput = document.querySelector("#modelInput");

const buttons = {
  oneShot: document.querySelector("#oneShotBtn"),
  checklist: document.querySelector("#checklistBtn"),
  questions: document.querySelector("#questionsBtn"),
  oracle: document.querySelector("#oracleBtn"),
  update: document.querySelector("#updateBtn"),
  copy: document.querySelector("#copyOutputBtn")
};

let scenarios = [];
let selectedScenario = null;
let latestOutput = null;
let latestQuestions = null;

init();

async function init() {
  setStatus("Loading scenarios");
  const response = await fetch("/api/scenarios");
  const data = await response.json();
  scenarios = data.scenarios || [];

  for (const scenario of scenarios) {
    const option = document.createElement("option");
    option.value = scenario.id;
    option.textContent = `${scenario.id} · ${scenario.title}`;
    scenarioSelect.append(option);
  }

  scenarioSelect.addEventListener("change", selectScenario);
  buttons.oneShot.addEventListener("click", () => runStage("one_shot"));
  buttons.checklist.addEventListener("click", () => runStage("checklist"));
  buttons.questions.addEventListener("click", () => runStage("questions"));
  buttons.oracle.addEventListener("click", () => runStage("oracle_answers"));
  buttons.update.addEventListener("click", () => runStage("update"));
  buttons.copy.addEventListener("click", copyOutput);

  selectScenario();
  setStatus("Ready");
}

function selectScenario() {
  selectedScenario = scenarios.find((scenario) => scenario.id === scenarioSelect.value) || scenarios[0];
  if (!selectedScenario) return;
  scenarioSelect.value = selectedScenario.id;
  scenarioDomain.textContent = selectedScenario.domain;
  scenarioId.textContent = selectedScenario.id;
  initialDescription.value = selectedScenario.initial_description;
  referenceWorkflow.textContent = JSON.stringify(selectedScenario.reference_workflow, null, 2);
  output.textContent = "";
  answers.value = "";
  latestOutput = null;
  latestQuestions = null;
}

async function runStage(stage) {
  if (!selectedScenario) return;
  setBusy(true);
  setStatus(`Running ${stage}`);

  try {
    const scenarioForRequest = {
      ...selectedScenario,
      initial_description: initialDescription.value
    };

    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        stage,
        model: modelInput.value.trim(),
        scenario: scenarioForRequest,
        answers: answers.value,
        previousOutput: latestOutput?.parsed || latestOutput,
        questions: latestQuestions?.parsed || latestQuestions
      })
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Run failed");

    latestOutput = result;
    output.textContent = JSON.stringify(result.parsed || result, null, 2);

    if (stage === "questions" && result.parsed?.clarification_questions) {
      latestQuestions = result;
      answers.value = result.parsed.clarification_questions
        .map((item) => `${item.id}. ${item.question}\nAnswer: `)
        .join("\n\n");
    }

    if (stage === "oracle_answers" && result.parsed?.answers) {
      answers.value = result.parsed.answers
        .map((item) => `${item.question_id}. ${item.question}\nAnswer: ${item.answer}`)
        .join("\n\n");
    }

    setStatus(`Saved run ${result.id}`);
  } catch (error) {
    output.textContent = JSON.stringify({ error: error.message }, null, 2);
    setStatus("Error");
  } finally {
    setBusy(false);
  }
}

async function copyOutput() {
  await navigator.clipboard.writeText(output.textContent);
  setStatus("Copied");
}

function setBusy(isBusy) {
  Object.values(buttons).forEach((button) => {
    button.disabled = isBusy;
  });
}

function setStatus(message) {
  statusEl.textContent = message;
}

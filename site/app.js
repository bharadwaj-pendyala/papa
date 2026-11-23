const hero = document.querySelector(".proof");
const draft = document.getElementById("draft");
const statusEl = document.getElementById("status");
const panel = document.getElementById("panel");
const rendered = document.getElementById("rendered");
const tips = document.getElementById("tips");

const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
setTimeout(() => { hero.dataset.state = "after"; }, reduceMotion ? 0 : 2600);
hero.addEventListener("click", () => {
  hero.dataset.state = hero.dataset.state === "after" ? "before" : "after";
});

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    await navigator.clipboard.writeText(document.getElementById(button.dataset.copy).textContent);
    button.textContent = "Copied";
    setTimeout(() => { button.textContent = "Copy"; }, 1600);
  });
});

const COUNTS = [
  ["very_hard_sentences", "very hard sentence", "very-hard-sentence"],
  ["hard_sentences", "hard sentence", "hard-sentence"],
  ["passive", "passive", "passive"],
  ["complex_phrases", "complex phrase", "complex-phrase"],
  ["adverbs", "adverb", "adverb"],
];

const GLUE = `
import json
from papa import analyze
from papa.reporters.html import _render_spans
from papa.reporters.json_report import file_payload

def check(text):
    analysis = analyze(text, path="draft.md")
    return json.dumps({"html": _render_spans(analysis.source, analysis.findings),
                       "report": file_payload(analysis)})
`;

async function loadGrader() {
  const { wheel } = await (await fetch("assets/wheel.json")).json();
  const pyodide = await loadPyodide();
  await pyodide.loadPackage(["micropip", "nltk", "setuptools"]);
  // textstat counts syllables with NLTK's CMU dictionary. A browser cannot run
  // nltk.download, so the site ships the corpus next to the wheel.
  const corpus = new Uint8Array(await (await fetch("assets/cmudict.zip")).arrayBuffer());
  pyodide.FS.mkdirTree("/home/pyodide/nltk_data/corpora");
  pyodide.FS.writeFile("/home/pyodide/nltk_data/corpora/cmudict.zip", corpus);
  await pyodide.pyimport("micropip").install(new URL(`assets/${wheel}`, location.href).href);
  pyodide.runPython("import nltk; nltk.data.path.insert(0, '/home/pyodide/nltk_data')");
  pyodide.runPython(GLUE);
  return pyodide.globals.get("check");
}

function plural(n, noun) {
  return n === 1 || noun === "passive" ? `${n} ${noun}` : `${n} ${noun}s`;
}

function show(result) {
  const { score, findings } = result.report;
  document.getElementById("grade-num").textContent = Math.max(0, Math.round(score.consensus));
  document.getElementById("grade-label").textContent = score.reading_grade.replace(/^Grade \d+, /, "");
  document.getElementById("counts").innerHTML = COUNTS
    .filter(([key]) => score[key] > 0)
    .map(([key, noun, cls]) => `<li class="hl-${cls}">${plural(score[key], noun)}</li>`)
    .join("") || "<li>No flagged sentences or words</li>";
  const grade = (x) => Math.max(0, x).toFixed(1);
  document.getElementById("formulas").textContent =
    `mean of ARI ${grade(score.ari)}, FK ${grade(score.flesch_kincaid)}, Fog ${grade(score.gunning_fog)} · ${plural(score.sentences, "sentence")}`;
  rendered.innerHTML = result.html;
  const byCategory = new Map(findings.map((f) => [f.category, f.hint]));
  if (byCategory.has("complex-phrase")) {
    byCategory.set("complex-phrase", "Use the plainer phrase. Hover a purple highlight to see it.");
  }
  const hints = [...new Set(byCategory.values())].filter(Boolean);
  tips.innerHTML = hints.map((h) => `<li>${h.replace(/[<>&]/g, (c) => `&#${c.charCodeAt(0)};`)}</li>`).join("");
  panel.hidden = false;
}

let timer;
loadGrader().then((check) => {
  const run = () => {
    if (!draft.value.trim()) {
      panel.hidden = true;
      rendered.textContent = "Type or paste some prose on the left.";
      tips.innerHTML = "";
      return;
    }
    show(JSON.parse(check(draft.value)));
  };
  statusEl.textContent = "Updates as you type";
  draft.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(run, 250); });
  run();
}).catch((error) => {
  statusEl.textContent = "The grader did not load. Reload the page, or run pipx install papa-lint.";
  console.error(error);
});

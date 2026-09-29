const expressionEl = document.getElementById("expression");
const resultEl = document.getElementById("result");

let expression = "";
let justEvaluated = false;

// Display symbols -> Python operators understood by /api/calc.
const toApi = (text) =>
  text.replace(/×/g, "*").replace(/÷/g, "/").replace(/−/g, "-").replace(/\^/g, "**");

function render() {
  resultEl.classList.remove("error");
  resultEl.textContent = expression || "0";
}

function formatNumber(n) {
  return Number.isInteger(n) ? String(n) : String(parseFloat(n.toPrecision(12)));
}

function input(value) {
  // After "=", a digit starts fresh; an operator continues from the result.
  if (justEvaluated && /[\d.(]/.test(value)) expression = "";
  justEvaluated = false;
  expressionEl.textContent = "";
  expression += value;
  render();
}

function clearAll() {
  expression = "";
  expressionEl.textContent = "";
  justEvaluated = false;
  render();
}

function backspace() {
  expression = expression.slice(0, -1);
  justEvaluated = false;
  render();
}

async function equals() {
  if (!expression) return;
  try {
    const response = await fetch("/api/calc", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expression: toApi(expression) }),
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "Invalid expression";
      throw new Error(detail);
    }
    expressionEl.textContent = expression + " =";
    expression = formatNumber(data.result);
    justEvaluated = true;
    render();
  } catch (err) {
    resultEl.textContent = err.message || "Something went wrong";
    resultEl.classList.add("error");
  }
}

document.querySelector(".keys").addEventListener("click", (event) => {
  const key = event.target.closest("button");
  if (!key) return;
  const { action, value } = key.dataset;
  if (action === "clear") clearAll();
  else if (action === "backspace") backspace();
  else if (action === "equals") equals();
  else if (value) input(value);
});

const keyMap = { "*": "×", "/": "÷", "-": "−", "+": "+", "^": "^", "%": "%", "(": "(", ")": ")", ".": "." };

document.addEventListener("keydown", (event) => {
  if (/^\d$/.test(event.key)) input(event.key);
  else if (keyMap[event.key]) input(keyMap[event.key]);
  else if (event.key === "Enter" || event.key === "=") { event.preventDefault(); equals(); }
  else if (event.key === "Backspace") backspace();
  else if (event.key === "Escape") clearAll();
  else return;
  event.preventDefault();
});

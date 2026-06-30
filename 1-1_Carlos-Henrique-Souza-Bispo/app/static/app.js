const form = document.querySelector("#churn-form");
const errorBox = document.querySelector("#form-error");
const results = document.querySelector("#results");
const submitButton = form.querySelector('button[type="submit"]');

const samples = {
  high: {
    customer_id: "risco-demo",
    gender: "Female",
    senior_citizen: "0",
    partner: "No",
    dependents: "No",
    tenure: "3",
    phone_service: "Yes",
    multiple_lines: "No",
    internet_service: "Fiber optic",
    online_security: "No",
    online_backup: "No",
    device_protection: "No",
    tech_support: "No",
    streaming_tv: "Yes",
    streaming_movies: "Yes",
    contract: "Month-to-month",
    paperless_billing: "Yes",
    payment_method: "Electronic check",
    monthly_charges: "95.50",
    total_charges: "286.50",
  },
  low: {
    customer_id: "estavel-demo",
    gender: "Male",
    senior_citizen: "0",
    partner: "Yes",
    dependents: "Yes",
    tenure: "65",
    phone_service: "Yes",
    multiple_lines: "Yes",
    internet_service: "DSL",
    online_security: "Yes",
    online_backup: "Yes",
    device_protection: "Yes",
    tech_support: "Yes",
    streaming_tv: "No",
    streaming_movies: "No",
    contract: "Two year",
    paperless_billing: "No",
    payment_method: "Bank transfer (automatic)",
    monthly_charges: "64.20",
    total_charges: "4173.00",
  },
};

function setFormValues(values) {
  Object.entries(values).forEach(([name, value]) => {
    const input = form.elements.namedItem(name);
    if (input) input.value = value;
  });
  syncDependentFields();
}

function syncDependentFields() {
  const internet = form.elements.namedItem("internet_service").value;
  const noInternet = internet === "No";
  document.querySelectorAll("[data-addon]").forEach((select) => {
    if (noInternet) {
      select.dataset.previous = select.value;
      select.value = "No internet service";
    } else if (select.value === "No internet service") {
      select.value = select.dataset.previous || "No";
    }
  });

  const phone = form.elements.namedItem("phone_service").value;
  const lines = form.elements.namedItem("multiple_lines");
  if (phone === "No") {
    lines.dataset.previous = lines.value;
    lines.value = "No phone service";
  } else if (lines.value === "No phone service") {
    lines.value = lines.dataset.previous || "No";
  }
}

document.querySelectorAll("[data-sample]").forEach((button) => {
  button.addEventListener("click", () => setFormValues(samples[button.dataset.sample]));
});

form.elements.namedItem("internet_service").addEventListener("change", syncDependentFields);
form.elements.namedItem("phone_service").addEventListener("change", syncDependentFields);

function serializeForm() {
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.senior_citizen = Number(payload.senior_citizen);
  payload.tenure = Number(payload.tenure);
  payload.monthly_charges = Number(payload.monthly_charges);
  payload.total_charges = Number(payload.total_charges);
  if (!payload.customer_id) delete payload.customer_id;
  return payload;
}

function renderResult(data) {
  const probability = data.churn_probability;
  const gauge = document.querySelector("#risk-gauge");
  const colors = { baixo: "#1b6f62", moderado: "#d18d27", alto: "#e97958" };
  gauge.style.setProperty("--risk-angle", `${probability * 360}deg`);
  gauge.style.setProperty("--risk-color", colors[data.risk_level]);
  document.querySelector("#risk-value").textContent = data.churn_percentage;

  const pill = document.querySelector("#risk-pill");
  pill.textContent = `risco ${data.risk_level}`;
  pill.style.color = colors[data.risk_level];
  pill.style.backgroundColor = `${colors[data.risk_level]}1f`;
  document.querySelector("#confidence-note").textContent = data.confidence_note;
  document.querySelector("#latency").textContent =
    `${data.latency_ms.toFixed(1)} ms · ${data.model_source}`;

  document.querySelector("#factors-list").innerHTML = data.factors
    .map(
      (factor) => `
        <div class="factor">
          <strong>${escapeHtml(factor.feature)} · ${escapeHtml(factor.value)}</strong>
          <b class="${factor.direction === "reduz" ? "down" : ""}">
            ${factor.direction === "aumenta" ? "↑ aumenta" : "↓ reduz"}
          </b>
          <p>${escapeHtml(factor.explanation)}</p>
        </div>`,
    )
    .join("");

  document.querySelector("#recommendations").innerHTML = data.recommendations
    .map(
      (item) => `
        <li>
          <strong>
            ${escapeHtml(item.action)}
            <span class="priority">${escapeHtml(item.priority)}</span>
          </strong>
          <p>${escapeHtml(item.reason)}</p>
        </li>`,
    )
    .join("");

  const warnings = document.querySelector("#warnings");
  warnings.hidden = data.guardrail_warnings.length === 0;
  warnings.innerHTML = data.guardrail_warnings
    .map((warning) => `<div>⚠ ${escapeHtml(warning)}</div>`)
    .join("");

  results.hidden = false;
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = String(value);
  return element.innerHTML;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.hidden = true;
  submitButton.disabled = true;
  const originalLabel = submitButton.querySelector("span").textContent;
  submitButton.querySelector("span").textContent = "Analisando sinais…";

  try {
    const response = await fetch("/api/v1/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(serializeForm()),
    });
    const data = await response.json();
    if (!response.ok) {
      const details = (data.details || [])
        .map((item) => `${item.field}: ${item.message}`)
        .join(" ");
      throw new Error(details || data.message || "Não foi possível analisar o perfil.");
    }
    renderResult(data);
  } catch (error) {
    errorBox.textContent =
      error instanceof Error
        ? error.message
        : "O serviço está temporariamente indisponível. Tente novamente.";
    errorBox.hidden = false;
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector("span").textContent = originalLabel;
  }
});

syncDependentFields();


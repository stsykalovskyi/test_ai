(function () {
  const q = (selector) => document.querySelector(selector);

  function formToJSON(form) {
    const data = new FormData(form);
    const payload = {};
    for (const [key, value] of data.entries()) {
      if (value === "") {
        continue;
      }
      if (["max_epochs", "batch_size"].includes(key)) {
        payload[key] = Number(value);
      } else if (key === "learning_rate") {
        payload[key] = Number(value);
      } else {
        payload[key] = value;
      }
    }
    return payload;
  }

  async function postJSON(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const text = await response.text();
    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch (error) {
      data = { error: "Invalid JSON response", raw: text };
    }
    if (!response.ok) {
      throw data;
    }
    return data;
  }

  function displayOutput(element, payload) {
    element.textContent = JSON.stringify(payload, null, 2);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const inflectForm = q("#inflect-form");
    const inflectOutput = q("#inflect-output");
    if (inflectForm && inflectOutput) {
      inflectForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        displayOutput(inflectOutput, { status: "pending" });
        try {
          const payload = formToJSON(inflectForm);
          const result = await postJSON("/api/morphology/inflect/", payload);
          displayOutput(inflectOutput, result);
        } catch (error) {
          displayOutput(inflectOutput, error);
        }
      });
    }

    const trainForm = q("#train-form");
    const trainOutput = q("#train-output");
    if (trainForm && trainOutput) {
      trainForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        displayOutput(trainOutput, { status: "pending" });
        try {
          const payload = formToJSON(trainForm);
          const result = await postJSON("/api/morphology/train/", payload);
          displayOutput(trainOutput, result);
        } catch (error) {
          displayOutput(trainOutput, error);
        }
      });
    }
  });
})();

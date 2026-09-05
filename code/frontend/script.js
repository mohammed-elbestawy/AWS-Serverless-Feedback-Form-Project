const API_URL = "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod";

const form = document.getElementById("feedback-form");
const submitBtn = document.getElementById("submit-btn");
const statusBox = document.getElementById("status");
const counterEl = document.getElementById("counter");

async function loadStats() {
  try {
    const res = await fetch(`${API_URL}/stats`);
    if (!res.ok) return;
    const data = await res.json();
    counterEl.textContent = data.total_messages ?? 0;
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

function showStatus(message, type) {
  statusBox.textContent = message;
  statusBox.className = `status ${type}`;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  showStatus("", "");

  const payload = {
    name: form.name.value.trim(),
    email: form.email.value.trim(),
    subject: form.subject.value.trim(),
    category: form.category.value,
    message: form.message.value.trim(),
  };

  if (Object.values(payload).some((v) => !v)) {
    showStatus("Please fill in all fields.", "error");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Sending...";

  try {
    const res = await fetch(`${API_URL}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Something went wrong.");
    }

    showStatus(data.message || "Message sent successfully!", "success");
    form.reset();
    loadStats();
  } catch (err) {
    showStatus(err.message || "Failed to send message. Please try again.", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Send Message";
  }
});

loadStats();

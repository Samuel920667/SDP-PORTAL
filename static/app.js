const form       = document.getElementById("petition-form");
const statusEl   = document.getElementById("status");
const backBtn    = document.getElementById("back-btn");
const nextBtn    = document.getElementById("next-btn");
const saveBtn    = document.getElementById("save-btn");
const steps      = [...document.querySelectorAll(".form-step")];
const stepItems  = [...document.querySelectorAll(".step-item")];
let current = 1;

const themeToggle = document.getElementById("theme-toggle");
const iconMoon = themeToggle.querySelector(".icon-moon");
const iconSun  = themeToggle.querySelector(".icon-sun");
const savedTheme = localStorage.getItem("petition-theme");
if (savedTheme === "light") document.body.dataset.theme = "light";
function updateThemeToggle() {
  const light = document.body.dataset.theme === "light";
  themeToggle.setAttribute("aria-pressed", String(light));
  themeToggle.setAttribute("aria-label", light ? "Switch to dark theme" : "Switch to light theme");
  iconMoon.style.display = light ? "none" : "block";
  iconSun.style.display  = light ? "block" : "none";
}
themeToggle.addEventListener("click", () => {
  const light = document.body.dataset.theme !== "light";
  document.body.dataset.theme = light ? "light" : "dark";
  localStorage.setItem("petition-theme", light ? "light" : "dark");
  updateThemeToggle();
});
updateThemeToggle();

function showStep(n) {
  current = n;
  steps.forEach((s, i)    => s.classList.toggle("active", i + 1 === n));
  stepItems.forEach((el, i) => {
    el.classList.toggle("active", i + 1 === n);
    el.classList.toggle("done",   i + 1 < n);
  });
  backBtn.disabled = n === 1;
  nextBtn.hidden   = n === 3;
  saveBtn.hidden   = n !== 3;
  if (n === 3) buildReview();
}

function validate() {
  for (const el of steps[current - 1].querySelectorAll("[required]")) {
    if (!el.checkValidity()) { el.reportValidity(); return false; }
  }
  return true;
}

function val(id) { return (document.getElementById(id)?.value || "").trim(); }

function buildReview() {
  const rows = [
    ["Title",           val("title")],
    ["Background",      val("background")],
    ["Grievance",       val("grievance")],
    ["Request",         val("request")],
    ["Evidence",        val("evidence") || "—"],
    ["Full Name",       val("petitioner")],
    ["Student ID",      val("student_id")],
    ["Faculty / Dept.", val("faculty")],
    ["Email",           val("email")],
    ["Level",           val("level") || "—"],
  ];
  document.getElementById("review-box").innerHTML = rows
    .map(([l, v]) =>
      `<div class="review-row">
         <span class="review-label">${l}</span>
         <span class="review-value">${v.replace(/\n/g, "<br>")}</span>
       </div>`)
    .join("");
}

nextBtn.addEventListener("click", () => { if (validate()) showStep(current + 1); });
backBtn.addEventListener("click", () => showStep(current - 1));

// Title suggestions
document.getElementById("suggest-btn").addEventListener("click", async () => {
  const btn = document.getElementById("suggest-btn");
  btn.disabled = true; btn.textContent = "…";
  try {
    const res = await fetch("/api/suggest-title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ background: val("background"), grievance: val("grievance") }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    const box = document.getElementById("suggestions");
    box.innerHTML = data.suggestions
      .map(s => `<button type="button" class="chip">${s}</button>`)
      .join("");
    box.querySelectorAll(".chip").forEach(c =>
      c.addEventListener("click", () => { document.getElementById("title").value = c.textContent; })
    );
  } catch (e) {
    statusEl.textContent = e.message;
    statusEl.className = "status-msg err";
  }
  btn.disabled = false; btn.textContent = "Suggest";
});

// Save & generate PDF
form.addEventListener("submit", async e => {
  e.preventDefault();
  if (!validate()) return;
  const decl = document.getElementById("declaration");
  if (!decl.checked) { decl.reportValidity(); return; }

  statusEl.textContent = "Saving your petition…";
  statusEl.className = "status-msg";
  saveBtn.disabled = true;

  const payload = {};
  new FormData(form).forEach((v, k) => { payload[k] = v; });

  try {
    const res = await fetch("/api/petitions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not save petition.");

    statusEl.textContent = "Petition saved. Your PDF is ready to download.";
    const card = document.getElementById("download-card");
    const link = document.getElementById("download-link");
    link.href = `/petition/${data.id}/pdf`;
    card.hidden = false;
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.className = "status-msg err";
    saveBtn.disabled = false;
  }
});

// Cookie & Privacy popup
(function () {
  const cookieOverlay  = document.getElementById('cookie-overlay');
  const privacyOverlay = document.getElementById('privacy-overlay');
  const COOKIE_KEY     = 'sdp-cookie-consent';

  document.getElementById('privacy-year').textContent = new Date().getFullYear();
  document.getElementById('fyear').textContent = new Date().getFullYear();

  if (!localStorage.getItem(COOKIE_KEY)) {
    cookieOverlay.hidden = false;
  }

  document.getElementById('cookie-accept').addEventListener('click', () => {
    localStorage.setItem(COOKIE_KEY, 'accepted');
    cookieOverlay.hidden = true;
  });

  document.getElementById('cookie-decline').addEventListener('click', () => {
    localStorage.setItem(COOKIE_KEY, 'declined');
    cookieOverlay.hidden = true;
  });

  document.getElementById('privacy-link').addEventListener('click', () => {
    cookieOverlay.hidden = true;
    privacyOverlay.hidden = false;
  });

  document.getElementById('privacy-close').addEventListener('click', () => {
    privacyOverlay.hidden = true;
    cookieOverlay.hidden = false;
  });

  document.getElementById('privacy-back').addEventListener('click', () => {
    privacyOverlay.hidden = true;
    cookieOverlay.hidden = false;
  });

  // close on backdrop click
  [cookieOverlay, privacyOverlay].forEach(el => {
    el.addEventListener('click', e => {
      if (e.target === el) {
        el.hidden = true;
        if (el === privacyOverlay) cookieOverlay.hidden = false;
      }
    });
  });
})();


(function () {
  const el = document.getElementById("typewriter");
  if (!el) return;
  const phrases = [
    "Formal Petition",
    "Your Voice",
    "Change Today",
    "Student Rights",
    "A Strong Case",
    "Your Grievance",
  ];
  let pi = 0, ci = 0, deleting = false;
  const TYPE_SPEED = 80, DELETE_SPEED = 40, PAUSE = 1800;

  function tick() {
    const phrase = phrases[pi];
    if (!deleting) {
      el.textContent = phrase.slice(0, ++ci);
      if (ci === phrase.length) { deleting = true; setTimeout(tick, PAUSE); return; }
    } else {
      el.textContent = phrase.slice(0, --ci);
      if (ci === 0) { deleting = false; pi = (pi + 1) % phrases.length; }
    }
    setTimeout(tick, deleting ? DELETE_SPEED : TYPE_SPEED);
  }
  tick();
})();

showStep(1);

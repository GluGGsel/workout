const START_DATE = new Date('2025-11-12T00:00:00'); // Tag 1

async function fetchState(){ return (await fetch("/api/state")).json(); }

const exercises = [
  { key:"squats",  label:"Squats" },
  { key:"situps",  label:"Crunches" }, // Backend-Key bleibt 'situps'
  { key:"pushups", label:"Push Ups" }
];

function formatDateForDay(day){
  const d = new Date(START_DATE.getTime());
  d.setDate(d.getDate() + (day - 1));
  const dd = String(d.getDate()).padStart(2,'0');
  const mm = String(d.getMonth()+1).padStart(2,'0');
  const yyyy = d.getFullYear();
  return `${dd}.${mm}.${yyyy}`;
}

function renderPerson(containerId, personKey, day, checks){
  const cont = document.getElementById(containerId);
  cont.innerHTML = "";

  exercises.forEach(e=>{
    const row = document.createElement("div");
    row.className = "exercise";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !!checks[e.key];
    cb.style.display = "none";

    const label = document.createElement("span");
    if (cb.checked){
      label.className = "check";
      label.textContent = "✓";
    } else {
      label.textContent = `${day} ${e.label}`;
    }

    row.addEventListener("click", async ()=>{
      await fetch("/api/toggle", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ person:personKey, exercise:e.key })
      });
      loadAndRender();
    });

    row.appendChild(cb);
    row.appendChild(label);
    cont.appendChild(row);
  });
}

async function loadAndRender(){
  const s = await fetchState();

  document.getElementById("day").textContent = s.day;
  const dateEl = document.getElementById("date");
  if (dateEl) dateEl.textContent = formatDateForDay(s.day);

  renderPerson("maleExercises",   "male",   s.day, s.male);
  renderPerson("femaleExercises", "female", s.day, s.female);

  const maleDone   = Object.values(s.male).every(Boolean);
  const femaleDone = Object.values(s.female).every(Boolean);
  const btn = document.getElementById("nextDayBtn");
  if (maleDone && femaleDone) btn.classList.remove("disabled");
  else btn.classList.add("disabled");
}

document.getElementById("nextDayBtn").addEventListener("click", async ()=>{
  const btn = document.getElementById("nextDayBtn");
  if (btn.classList.contains("disabled")) return;
  const r = await fetch("/api/next_day", { method:"POST" });
  if (r.ok) await loadAndRender();
  else alert("Nicht abgeschlossen!");
});

loadAndRender();

<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>Workout</title>
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <style>
    :root{
      --male-bg:#e9f2ff; --male-border:#6aa6ff; --male-accent:#2c6cff;
      --female-bg:#ffe9f4; --female-border:#ff86b7; --female-accent:#e33682;
      --ok:#16a34a; --muted:#666;
    }
    html,body{height:100%}
    body{font-family:Arial,Helvetica,sans-serif;padding:24px;background:#fafafa;color:#111;-webkit-text-size-adjust:100%}
    h1{margin:0 0 6px}
    .muted{color:var(--muted);font-size:0.95em;margin:4px 0 16px}
    .container{display:flex;gap:20px;flex-wrap:wrap}
    .panel{border:2px solid #ddd;border-radius:12px;padding:18px;width:340px;background:white;
      transition:box-shadow .15s ease, border-color .15s ease, background .15s ease}
    .panel.male{background:var(--male-bg);border-color:var(--male-border)}
    .panel.female{background:var(--female-bg);border-color:var(--female-border)}
    .panel h2{margin:0 0 10px;font-size:1.4rem}
    .exercise{display:flex;align-items:center;gap:14px;margin:12px 0;padding:12px 10px;cursor:pointer;user-select:none;
      -webkit-tap-highlight-color:transparent;touch-action:manipulation;border-radius:10px}
    .readonly .exercise{opacity:.6;pointer-events:none}
    .exercise input[type="checkbox"]{display:none}
    .check{font-weight:bold;color:var(--ok);font-size:36px;line-height:1}
    .chip{display:inline-block;padding:6px 10px;border-radius:999px;font-size:.95rem;font-weight:600}
    .chip.male{background:rgba(44,108,255,.12);color:var(--male-accent);border:1px solid var(--male-border)}
    .chip.female{background:rgba(227,54,130,.12);color:var(--female-accent);border:1px solid var(--female-border)}
    .status{margin:10px 0 16px;font-size:.95rem}
    .status .done{color:var(--ok);font-weight:700}
    .status .wait{color:#b45309;font-weight:700}
    button{padding:12px 16px;border-radius:12px;border:1px solid #ccc;background:#fff;cursor:pointer;
      font-size:1rem;min-height:48px;touch-action:manipulation}
    .disabled{opacity:.5;pointer-events:none}
    @media(max-width:768px){
      body{padding:18px;font-size:18px;line-height:1.35}
      h1{font-size:2rem}
      .container{flex-direction:column;gap:16px}
      .panel{width:100%;max-width:none}
      .exercise{padding:14px 12px;font-size:1.15rem}
      .check{font-size:42px}
      .muted{font-size:1rem}
      button{width:100%;font-size:1.1rem}
    }
  </style>
</head>
<body>
  <h1>Workout</h1>
  <div class="muted">Datum: <span id="date">–</span></div>
  <div>Aktueller Tag: <span id="day">1</span></div>
  <div id="overallStatus" class="status"></div>

  <div class="container">
    <div class="panel male" id="malePanel">
      <h2><span class="chip male">Mann</span></h2>
      <div id="maleExercises"></div>
    </div>
    <div class="panel female" id="femalePanel">
      <h2><span class="chip female">Frau</span></h2>
      <div id="femaleExercises"></div>
    </div>
  </div>

  <div style="margin-top:18px">
    <button id="nextDayBtn" class="disabled">Nächster Tag</button>
  </div>

  <script>
    const START_DATE = new Date('2025-11-12T00:00:00');
    const params = new URLSearchParams(window.location.search);
    const view = (params.get('view') || '').toLowerCase();
    const clickableFor = view === 'mann' ? 'male' : view === 'frau' ? 'female' : '';

    async function fetchState(){ return (await fetch("/api/state")).json(); }

    const exercises = [
      { key:"squats",  label:"Squats" },
      { key:"situps",  label:"Crunches" },
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

    function renderPerson(containerId, personKey, day, checks, readOnly){
      const panel = document.getElementById(containerId).parentElement;
      const cont = document.getElementById(containerId);
      cont.innerHTML = "";
      panel.classList.toggle('readonly', !!readOnly);

      exercises.forEach(e=>{
        const row = document.createElement("div");
        row.className = "exercise";
        const cb = document.createElement("input");
        cb.type = "checkbox"; cb.checked = !!checks[e.key]; cb.style.display = "none";
        const label = document.createElement("span");
        if (cb.checked){ label.className="check"; label.textContent="✓"; }
        else { label.textContent = `${day} ${e.label}`; }

        if (!readOnly){
          row.addEventListener("click", async ()=>{
            await fetch("/api/toggle", {
              method:"POST", headers:{"Content-Type":"application/json"},
              body:JSON.stringify({ person:personKey, exercise:e.key })
            });
            loadAndRender();
          }, {passive:true});
        }
        row.appendChild(cb); row.appendChild(label); cont.appendChild(row);
      });
    }

    function updateStatus(s){
      const maleDone = Object.values(s.male).every(Boolean);
      const femaleDone = Object.values(s.female).every(Boolean);
      const st = document.getElementById("overallStatus");
      if (maleDone && femaleDone)
        st.innerHTML = '<span class="done">Beide fertig.</span> Weiter geht’s morgen.';
      else if (maleDone && !femaleDone)
        st.innerHTML = '<span class="done">Mann ist fertig</span> — <span class="wait">Frau zögert noch.</span>';
      else if (!maleDone && femaleDone)
        st.innerHTML = '<span class="done">Frau ist fertig</span> — <span class="wait">Mann zögert noch.</span>';
      else st.textContent = 'Niemand fertig. Alle tun so, als wäre Stretching schon Training.';
    }

    async function loadAndRender(){
      const s = await fetchState();
      document.getElementById("day").textContent = s.day;
      const dateEl = document.getElementById("date");
      if (dateEl) dateEl.textContent = formatDateForDay(s.day);
      const maleRO = clickableFor && clickableFor!=='male';
      const femaleRO = clickableFor && clickableFor!=='female';
      renderPerson("maleExercises","male",s.day,s.male,maleRO);
      renderPerson("femaleExercises","female",s.day,s.female,femaleRO);
      const maleDone = Object.values(s.male).every(Boolean);
      const femaleDone = Object.values(s.female).every(Boolean);
      const btn = document.getElementById("nextDayBtn");
      if (maleDone && femaleDone) btn.classList.remove("disabled");
      else btn.classList.add("disabled");
      updateStatus(s);
    }

    document.getElementById("nextDayBtn").addEventListener("click", async ()=>{
      const btn = document.getElementById("nextDayBtn");
      if (btn.classList.contains("disabled")) return;
      const r = await fetch("/api/next_day",{method:"POST"});
      if (r.ok) await loadAndRender(); else alert("Nicht abgeschlossen!");
    });

    loadAndRender();
    setInterval(loadAndRender,5000);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)loadAndRender();});
  </script>
</body>
</html>

// A simulation as an EMBED of creator (the package of `htmlkit/simpackage.py`), on creator's `slxd-embed` protocol: it asks
// for its saved state (`ready`, answered with `restore`), tells the lesson its state after each step (`state`), its grade at
// an ending (`result`, before closing it), each decision (`interaction`) and that it is over (`complete`), and starts again
// on `reset`. Without a lesson that answers (opened on its own), it starts from the beginning after a moment.
// It is a plain script after the inlined player: `__simulation` and `__bridge` exist, and `__CK_UI__` is replaced with the
// texts of the interface.
(() => {
  const ui = __CK_UI__;
  const root = document.querySelector(".ck-sim");
  if (!root) return;
  const data = JSON.parse(root.querySelector(".ck-sim-data").textContent);
  const scenes = data.scenes || {};
  const WAIT = 1500;  // ms for the lesson to answer `ready` before starting without a saved state

  // creator's identifiers: [a-z][a-z0-9_]*, up to 64 characters (a scene id may hold "-")
  const identifier = (text) => {
    const clean = String(text || "").toLowerCase().replace(/[^a-z0-9_]/g, "_");
    return (/^[a-z]/.test(clean) ? clean : `e_${clean}`).slice(0, 64);
  };
  const letter = (i) => (i < 26 ? String.fromCharCode(97 + i) : `o${i}`);  // the option, as SCORM 1.2 takes a choice
  const grade = (score) => (data.max_score > 0 ? Math.max(0, Math.min(100, Math.round((100 * score) / data.max_score))) : 0);
  // the state the lesson keeps (at most 1,024 characters of JSON): where it is, its variables, points, ended, attempt, decisions
  const compact = (run) => ({ a: run.at, e: run.env || {}, s: run.score || 0, d: run.done ? 1 : 0, t: run.attempt || 1,
    n: run.decisions || 0 });

  const store = { sims: {} };
  let started = false;
  let closed = false;
  let last = "";
  let sims = [];

  function report(run) {
    const done = Boolean(run.done);
    if (done && !closed) {
      const ending = run.ending || run.at;
      const kind = (scenes[ending] || {}).ending;
      __bridge.send("result", { score: Number(run.score) || 0, maxScore: Math.max(0, Number(data.max_score) || 0),
        grade: grade(run.score || 0), ending: identifier(ending), kind: ["good", "mixed", "bad"].includes(kind) ? kind : "mixed" });
    }
    const state = compact(run);
    const text = JSON.stringify([state, done]);
    if (text !== last) {
      last = text;
      __bridge.send("state", { state, done });
    }
    if (done && !closed) __bridge.complete();
    closed = done;
  }

  const tracker = {
    state: store,
    simulation(id, run) {
      if (run === undefined) return store.sims[id] || null;
      store.sims[id] = run;
      if (started) report(run);
      return run;
    },
    interaction(entry) {
      __bridge.send("interaction", { attempt: entry.attempt || 1, n: entry.n || 1, response: letter(entry.choice || 0),
        description: String(entry.description || "").slice(0, 250), result: entry.result, weighting: entry.weighting || 1 });
    },
  };

  function start(saved) {
    if (started) return;
    if (saved && typeof saved === "object" && typeof saved.a === "string" && scenes[saved.a]) {
      const done = saved.d === 1;
      store.sims[data.id] = { at: saved.a, env: saved.e || {}, score: Number(saved.s) || 0, done, ending: done ? saved.a : null,
        path: [], attempt: Number(saved.t) || 1, decisions: Number(saved.n) || 0 };
      closed = done;
      last = JSON.stringify([compact(store.sims[data.id]), done]);
    }
    sims = __simulation.initSimulations(document, ui, tracker);
    started = true;
  }

  __bridge.listen((message) => {
    if (message.type === "restore") start(message.state);
    if (message.type === "reset") {
      start(null);
      closed = false;
      sims.forEach((sim) => sim.reset());
    }
  });
  setTimeout(() => start(null), WAIT);
})();

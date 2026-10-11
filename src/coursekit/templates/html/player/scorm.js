// SCORM tracking of one unit, on top of @studiolxd/scorm. Without an LMS (a preview from a folder) the runtime is the
// in-memory mock, so the package works the same and nothing is sent anywhere.
import { createScormSession } from "@studiolxd/scorm";

const value = (result, fallback) => (result && result.ok ? result.value : fallback);

export function createTracker(config) {
  let session = null;
  let api = null;
  const started = Date.now();
  try {
    session = createScormSession(config.standard === "2004" ? "2004" : "1.2", { noLmsBehavior: "mock" });
    session.initialize();
    api = session.api || null;
  } catch (error) {
    api = null;
  }
  const total = config.lessons.length;
  const hasQuiz = config.lessons.some((lesson) => lesson.type === "evaluation");
  const state = { visited: [], attempts: 0, best: null, location: null, sims: {}, interactions: 0 };

  const safe = (fn) => {
    try {
      return fn();
    } catch (error) {
      return undefined;
    }
  };

  const save = () => {
    if (!api) return;
    // SCORM 1.2 keeps 4096 characters: of each simulation only where it is, its state, its points and whether it ended
    const sims = {};
    Object.entries(state.sims).forEach(([id, run]) => {
      sims[id] = { a: run.at, e: run.env, s: run.score, d: run.done ? 1 : 0 };
    });
    safe(() => api.setSuspendData(JSON.stringify({ v: state.visited, a: state.attempts, b: state.best, s: sims, n: state.interactions })));
    safe(() => api.commit());
  };

  const restore = () => {
    if (!api) return state;
    const raw = value(safe(() => api.getSuspendData()), "");
    try {
      const saved = JSON.parse(raw || "{}");
      state.visited = Array.isArray(saved.v) ? saved.v.filter((n) => Number.isInteger(n) && n >= 0 && n < total) : [];
      state.attempts = Number.isInteger(saved.a) ? saved.a : 0;
      state.best = typeof saved.b === "number" ? saved.b : null;
      state.interactions = Number.isInteger(saved.n) ? saved.n : 0;
      Object.entries(saved.s && typeof saved.s === "object" ? saved.s : {}).forEach(([id, run]) => {
        state.sims[id] = { at: run.a, env: run.e || {}, score: Number(run.s) || 0, done: run.d === 1, path: [] };
      });
    } catch (error) {
      /* an unreadable record starts from scratch */
    }
    state.location = value(safe(() => api.getLocation()), "") || null;
    return state;
  };

  const progress = () => {
    if (!api) return;
    safe(() => api.setProgressMeasure(state.visited.length / total));
    if (state.visited.length === total && !hasQuiz) {
      safe(() => api.setComplete());
    } else if (state.visited.length === total && config.standard === "2004") {
      safe(() => api.setComplete());
    } else {
      safe(() => api.setIncomplete());
    }
  };

  return {
    state,
    hasQuiz,
    restore,
    visit(index, key) {
      if (!state.visited.includes(index)) state.visited.push(index);
      state.location = key;
      if (api) safe(() => api.setLocation(key));
      progress();
      save();
    },
    quiz({ score, passed, interactions }) {
      state.attempts += 1;
      state.best = state.best === null ? score : Math.max(state.best, score);
      if (api) {
        safe(() => api.setScore({ raw: score, min: 0, max: 100, scaled: score / 100 }));
        safe(() => (passed ? api.setPassed() : api.setFailed()));
        interactions.forEach((entry) => {
          safe(() => api.recordInteraction(state.interactions, entry));
          state.interactions += 1;
        });
      }
      save();
    },
    // The score of a unit without a test whose scored simulations have all ended.
    score(score) {
      if (api) safe(() => api.setScore({ raw: score, min: 0, max: 100, scaled: score / 100 }));
      save();
    },
    // The run of a simulation: read it (`simulation(id)`) or keep it (`simulation(id, run)`).
    simulation(id, run) {
      if (run === undefined) return state.sims[id] || null;
      state.sims[id] = run;
      save();
      return run;
    },
    interaction(entry) {
      if (api) safe(() => api.recordInteraction(state.interactions, entry));
      state.interactions += 1;
    },
    finish() {
      if (!api) return;
      safe(() => api.setSessionTime(Date.now() - started));
      safe(() => api.setExit("suspend"));
      safe(() => session.commit());
      safe(() => session.terminate());
    },
  };
}

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
  const state = { visited: [], attempts: 0, best: null, location: null };

  const safe = (fn) => {
    try {
      return fn();
    } catch (error) {
      return undefined;
    }
  };

  const save = () => {
    if (!api) return;
    safe(() => api.setSuspendData(JSON.stringify({ v: state.visited, a: state.attempts, b: state.best })));
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
        interactions.forEach((entry, i) => safe(() => api.recordInteraction(i, entry)));
      }
      save();
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

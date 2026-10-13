// The simulated LMS of `coursekit preview` and `coursekit assemble check`: the SCORM 1.2 (`API`) and 2004 (`API_1484_11`)
// runtimes over one record, as strict as a real platform. A value the standard does not admit is refused (`"false"` and
// its error code) and kept in `errors`, so a package that works here does not lose data on the client's LMS.

const VOCAB_12 = {
  "cmi.core.lesson_status": ["passed", "completed", "failed", "incomplete", "browsed", "not attempted"],
  "cmi.core.exit": ["time-out", "suspend", "logout", ""],
};
const VOCAB_2004 = {
  "cmi.completion_status": ["completed", "incomplete", "not attempted", "unknown"],
  "cmi.success_status": ["passed", "failed", "unknown"],
  "cmi.exit": ["time-out", "suspend", "logout", "normal", ""],
};
const TYPES = ["true-false", "choice", "fill-in", "matching", "performance", "sequencing", "likert", "numeric"];
const RESULTS_12 = ["correct", "wrong", "unanticipated", "neutral"];
const RESULTS_2004 = ["correct", "incorrect", "unanticipated", "neutral"];
const READ_ONLY_12 = ["cmi.core.student_id", "cmi.core.student_name", "cmi.core.credit", "cmi.core.entry", "cmi.core.total_time",
  "cmi.core.lesson_mode", "cmi.launch_data", "cmi.core._children", "cmi.interactions._count", "cmi.student_data.mastery_score"];
const READ_ONLY_2004 = ["cmi.learner_id", "cmi.learner_name", "cmi.credit", "cmi.entry", "cmi.total_time", "cmi.mode",
  "cmi.launch_data", "cmi._version", "cmi.interactions._count", "cmi.completion_threshold", "cmi.scaled_passing_score"];

const DECIMAL = /^-?\d+(\.\d+)?$/;
const TIME_12 = /^\d{2,4}:\d{2}:\d{2}(\.\d{1,2})?$/;
const DURATION = /^P(?!$)(\d+Y)?(\d+M)?(\d+D)?(T(?!$)(\d+H)?(\d+M)?(\d+(\.\d{1,2})?S)?)?$/;

const ERRORS_12 = { 0: "No error", 101: "General exception", 201: "Invalid argument error", 301: "Not initialized",
  401: "Not implemented error",
  403: "Element is read only", 405: "Incorrect data type" };
const ERRORS_2004 = { 0: "No error", 101: "General exception", 103: "Already initialized", 112: "Termination before initialization",
  113: "Termination after termination", 142: "Commit after termination", 122: "Store data before initialization", 123: "Store data after termination",
  132: "Retrieve data before initialization", 351: "General set failure", 404: "Data model element is read only",
  406: "Data model element type mismatch", 407: "Data model element value out of range" };

export const LIMITS = { "1.2": { suspend: 4096, location: 255, response: 255 }, "2004": { suspend: 64000, location: 1000, response: 4000 } };

const DEFAULTS_12 = {
  "cmi.core._children": "student_id,student_name,lesson_location,credit,lesson_status,entry,score,total_time,lesson_mode,exit,session_time",
  "cmi.core.student_id": "preview", "cmi.core.student_name": "Preview, Learner", "cmi.core.lesson_mode": "normal",
  "cmi.core.credit": "credit", "cmi.core.lesson_status": "not attempted", "cmi.core.total_time": "0000:00:00",
  "cmi.launch_data": "", "cmi.core.lesson_location": "", "cmi.suspend_data": "", "cmi.student_data.mastery_score": "",
};
const DEFAULTS_2004 = {
  "cmi._version": "1.0", "cmi.learner_id": "preview", "cmi.learner_name": "Preview, Learner", "cmi.mode": "normal",
  "cmi.credit": "credit", "cmi.completion_status": "unknown", "cmi.success_status": "unknown", "cmi.total_time": "PT0S",
  "cmi.launch_data": "", "cmi.location": "", "cmi.suspend_data": "", "cmi.completion_threshold": "", "cmi.scaled_passing_score": "",
};

// The keys the panel and the checker read, per standard.
export function keys(standard) {
  return standard === "2004" ? {
    status: "cmi.completion_status", success: "cmi.success_status", score: "cmi.score.raw", location: "cmi.location",
    progress: "cmi.progress_measure", entry: "cmi.entry", exit: "cmi.exit", time: "cmi.session_time", suspend: "cmi.suspend_data",
    response: "learner_response",
  } : {
    status: "cmi.core.lesson_status", success: null, score: "cmi.core.score.raw", location: "cmi.core.lesson_location",
    progress: null, entry: "cmi.core.entry", exit: "cmi.core.exit", time: "cmi.core.session_time", suspend: "cmi.suspend_data",
    response: "student_response",
  };
}

// Why the standard refuses `value` for `name` (an error code), or 0 when it admits it.
export function check(standard, name, value) {
  const is2004 = standard === "2004";
  const text = String(value);
  const limits = LIMITS[is2004 ? "2004" : "1.2"];
  const type = is2004 ? 406 : 405;
  const range = is2004 ? 407 : 405;
  if ((is2004 ? READ_ONLY_2004 : READ_ONLY_12).includes(name)) return is2004 ? 404 : 403;
  const vocab = (is2004 ? VOCAB_2004 : VOCAB_12)[name];
  if (vocab) return vocab.includes(text) ? 0 : type;
  if (name === "cmi.suspend_data") return text.length <= limits.suspend ? 0 : type;
  if (name === "cmi.core.lesson_location" || name === "cmi.location") return text.length <= limits.location ? 0 : type;
  if (/^cmi(\.core)?\.score\.(raw|min|max)$/.test(name)) {
    if (!DECIMAL.test(text)) return type;
    return !is2004 && (Number(text) < 0 || Number(text) > 100) ? range : 0;
  }
  if (name === "cmi.score.scaled") return DECIMAL.test(text) && Math.abs(Number(text)) <= 1 ? 0 : (DECIMAL.test(text) ? range : type);
  if (name === "cmi.progress_measure") return DECIMAL.test(text) && Number(text) >= 0 && Number(text) <= 1 ? 0 : range;
  if (name === "cmi.core.session_time") return TIME_12.test(text) ? 0 : type;
  if (name === "cmi.session_time") return DURATION.test(text) ? 0 : type;
  const field = /^cmi\.interactions\.\d+\.(.+)$/.exec(name);
  if (field) {
    const part = field[1];
    if (part === "id") return text && !/\s/.test(text) && text.length <= (is2004 ? 4000 : 255) ? 0 : type;
    if (part === "type") return (is2004 ? TYPES.concat(["long-fill-in", "other"]) : TYPES).includes(text) ? 0 : type;
    if (part === "result") return (is2004 ? RESULTS_2004 : RESULTS_12).includes(text) || DECIMAL.test(text) ? 0 : type;
    if (part === "weighting") return DECIMAL.test(text) ? 0 : type;
    if (part === "description") return is2004 ? (text.length <= 250 ? 0 : type) : 401;
    if (part === "student_response" || part === "learner_response") return text.length <= limits.response ? 0 : type;
    return 0;
  }
  return 0;
}

// The response of a choice: single characters a-z/0-9 separated by "," in 1.2, identifiers without spaces separated by
// "[,]" in 2004. Checked when the record says the interaction is a choice (its type may come before or after).
export function choiceProblem(standard, response) {
  if (response === "") return false;
  if (standard === "2004") return response.split("[,]").some((part) => !part || /\s/.test(part) || part.length > 250);
  return !/^\{?[0-9a-z](,[0-9a-z])*\}?$/.test(response);
}

export function createLms(standard, store, onCall = () => {}) {
  const is2004 = standard === "2004";
  const K = keys(standard);
  const defaults = is2004 ? DEFAULTS_2004 : DEFAULTS_12;
  const messages = is2004 ? ERRORS_2004 : ERRORS_12;
  let data = store.load() || {};
  let state = "new";  // new → open → closed
  let lastError = "0";
  const errors = [];
  let maxSuspend = 0;

  const fail = (code, name, value) => {
    lastError = String(code);
    errors.push({ code, name, value: value === undefined ? undefined : String(value), message: messages[code] || "" });
    return "false";
  };
  const indexes = () => {
    const seen = new Set();
    Object.keys(data.cmi || {}).forEach((k) => {
      const m = /^cmi\.interactions\.(\d+)\./.exec(k);
      if (m) seen.add(Number(m[1]));
    });
    return [...seen].sort((a, b) => a - b);
  };

  const initialize = () => {
    if (state === "open") return is2004 ? fail(103) : "true";
    data = store.load() || {};
    data.cmi = data.cmi || {};
    const resumed = data.closedWith === "suspend";
    // after a normal exit the LMS opens a new attempt and starts the record again
    if (!resumed && data.launched) data.cmi = {};
    data.cmi[K.entry] = resumed ? "resume" : "ab-initio";
    data.launched = true;
    delete data.closedWith;
    state = "open";
    store.save(data);
    return "true";
  };
  const getValue = (name) => {
    if (state !== "open") {
      fail(is2004 ? 132 : 301, name);
      return "";
    }
    if (name === "cmi.interactions._count") return String(indexes().length);
    if (name === "cmi.interactions._children") {
      return is2004 ? "id,type,objectives,timestamp,correct_responses,weighting,learner_response,result,latency,description"
        : "id,objectives,time,type,correct_responses,weighting,student_response,result,latency";
    }
    if (name === "cmi.objectives._count") return "0";
    const cmi = data.cmi || {};
    if (name in cmi) return cmi[name];
    if (name in defaults) return defaults[name];
    return "";
  };
  const setValue = (name, value) => {
    if (state !== "open") return fail(is2004 ? (state === "new" ? 122 : 123) : 301, name, value);
    const code = check(standard, name, value);
    if (code) return fail(code, name, value);
    const response = /^(cmi\.interactions\.\d+)\.(student_response|learner_response|type)$/.exec(name);
    if (response) {
      const base = response[1];
      const after = { ...data.cmi, [name]: String(value) };
      const reply = after[`${base}.${K.response}`];
      if (after[`${base}.type`] === "choice" && reply !== undefined && choiceProblem(standard, reply)) {
        return fail(is2004 ? 406 : 405, name, value);
      }
    }
    data.cmi[name] = String(value);
    if (name === "cmi.suspend_data") maxSuspend = Math.max(maxSuspend, String(value).length);
    return "true";
  };
  const commit = () => {
    if (state !== "open") return fail(is2004 ? 142 : 301);
    store.save(data);
    return "true";
  };
  const finish = () => {
    if (state !== "open") return fail(is2004 ? (state === "new" ? 112 : 113) : 301);
    state = "closed";
    data.closedWith = (data.cmi || {})[K.exit] === "suspend" ? "suspend" : "normal";
    store.save(data);
    return "true";
  };

  const wrap = (name, fn) => (...args) => {
    lastError = "0";
    const before = errors.length;
    const result = fn(...args);
    onCall({ name, args, result, error: errors.length > before ? errors[errors.length - 1] : null });
    return result;
  };
  const tools = {
    GetLastError: () => lastError,
    GetErrorString: (code) => messages[Number(code)] || "",
    GetDiagnostic: (code) => messages[Number(code)] || "",
  };
  return {
    api12: {
      LMSInitialize: wrap("LMSInitialize", initialize), LMSFinish: wrap("LMSFinish", finish),
      LMSGetValue: wrap("LMSGetValue", getValue), LMSSetValue: wrap("LMSSetValue", setValue), LMSCommit: wrap("LMSCommit", commit),
      LMSGetLastError: tools.GetLastError, LMSGetErrorString: tools.GetErrorString, LMSGetDiagnostic: tools.GetDiagnostic,
    },
    api2004: {
      Initialize: wrap("Initialize", initialize), Terminate: wrap("Terminate", finish),
      GetValue: wrap("GetValue", getValue), SetValue: wrap("SetValue", setValue), Commit: wrap("Commit", commit), ...tools,
    },
    record: () => data,
    reload: () => { data = store.load() || {}; },
    errors,
    maxSuspend: () => maxSuspend,
    indexes,
    defaults,
    keys: K,
  };
}

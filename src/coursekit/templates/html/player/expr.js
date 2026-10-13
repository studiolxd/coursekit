// Conditions of the simulations and of the adaptive blocks, the same language as coursekit/simulation.py:
// numbers, true, false, texts in double quotes (only with == and !=), variables (`risk`, `call.risk`),
// + - == != < <= > >= ! && || and parentheses.

const TOKEN = /\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)|(&&|\|\||==|!=|<=|>=|[<>!()+-])|"([^"\\]*)")/y;

function tokens(text) {
  const out = [];
  const source = String(text).trim();
  TOKEN.lastIndex = 0;
  while (TOKEN.lastIndex < source.length) {
    const start = TOKEN.lastIndex;
    const m = TOKEN.exec(source);
    if (!m || TOKEN.lastIndex === start) throw new Error(`invalid condition: ${source}`);
    if (m[4] !== undefined) out.push(["str", m[4]]);
    else if (m[1] !== undefined) out.push(["num", Number(m[1])]);
    else if (m[2] !== undefined) out.push(m[2] === "true" || m[2] === "false" ? ["num", m[2] === "true"] : ["var", m[2]]);
    else out.push(["op", m[3]]);
  }
  return out;
}

export function parse(text) {
  if (typeof text === "boolean") return ["num", text];
  const items = tokens(text);
  let i = 0;
  const peek = () => items[i];
  const take = (...ops) => {
    const item = items[i];
    if (item && item[0] === "op" && ops.includes(item[1])) {
      i += 1;
      return item[1];
    }
    return null;
  };
  const textOnly = (node) => {
    if (node[0] === "str") throw new Error(`a text is only compared with == or !=: ${text}`);
    return node;
  };
  const unary = () => {
    if (take("-")) return ["neg", textOnly(unary())];
    if (take("(")) {
      const node = or();
      if (!take(")")) throw new Error(`a parenthesis is not closed: ${text}`);
      return node;
    }
    const item = peek();
    if (!item || item[0] === "op") throw new Error(`invalid condition: ${text}`);
    i += 1;
    return item;
  };
  const sum = () => {
    let node = unary();
    let op = take("+", "-");
    while (op) {
      node = [op, textOnly(node), textOnly(unary())];
      op = take("+", "-");
    }
    return node;
  };
  const compare = () => {
    const node = sum();
    const op = take("==", "!=", "<", "<=", ">", ">=");
    if (!op) return textOnly(node);
    const right = sum();
    if (op !== "==" && op !== "!=") {
      textOnly(node);
      textOnly(right);
    }
    return [op, node, right];
  };
  const not = () => (take("!") ? ["!", not()] : compare());
  const and = () => {
    let node = not();
    while (take("&&")) node = ["&&", node, not()];
    return node;
  };
  function or() {
    let node = and();
    while (take("||")) node = ["||", node, and()];
    return node;
  }
  if (!items.length) throw new Error("empty condition");
  const node = or();
  if (i < items.length) throw new Error(`invalid condition: ${text}`);
  return node;
}

export function names(node) {
  if (node[0] === "var") return [node[1]];
  if (node[0] === "num" || node[0] === "str") return [];
  return node.slice(1).flatMap(names);
}

export function evaluate(node, env) {
  const [kind] = node;
  if (kind === "num" || kind === "str") return node[1];
  if (kind === "var") return Object.prototype.hasOwnProperty.call(env, node[1]) ? env[node[1]] : 0;
  if (kind === "!") return !evaluate(node[1], env);
  if (kind === "neg") return -evaluate(node[1], env);
  if (kind === "&&") return Boolean(evaluate(node[1], env)) && Boolean(evaluate(node[2], env));
  if (kind === "||") return Boolean(evaluate(node[1], env)) || Boolean(evaluate(node[2], env));
  const a = evaluate(node[1], env);
  const b = evaluate(node[2], env);
  switch (kind) {
    case "==": return a === b;
    case "!=": return a !== b;
    case "<": return a < b;
    case "<=": return a <= b;
    case ">": return a > b;
    case ">=": return a >= b;
    case "+": return a + b;
    default: return a - b;
  }
}

export function test(condition, env) {
  if (condition === undefined || condition === null) return true;
  return Boolean(evaluate(parse(condition), env));
}

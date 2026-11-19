// Shared helpers: DOM builders, number and date formatting, scales. No data values live here.
const SVG_NS = 'http://www.w3.org/2000/svg';
const MONTHS_PER_YEAR = 12;

function build(node, attrs, kids) {
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return node;
}

export const h = (tag, attrs, ...kids) => build(document.createElement(tag), attrs, kids);
export const s = (tag, attrs, ...kids) => build(document.createElementNS(SVG_NS, tag), attrs, kids);

export function fill(id, ...kids) {
  const node = document.getElementById(id);
  node.replaceChildren(...kids.flat().filter((k) => k !== null && k !== undefined && k !== false));
  return node;
}

export const MINUS = '−';
export const num = (v, d = 0) =>
  v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
export function signed(v, d = 0) {
  const text = num(Math.abs(v), d);
  if (Number(text.replace(/,/g, '')) === 0) return text;
  return (v > 0 ? '+' : MINUS) + text;
}
export const isPerShare = (unit) => unit === 'USD_per_share';
export const digits = (unit) => (isPerShare(unit) ? 2 : 0);

// Dollar amount for prose: "$1.5 billion", "$950 million", "$0.45 a share".
export function dollars(v, unit) {
  const a = Math.abs(v);
  if (isPerShare(unit)) return `$${num(a, 2)} a share`;
  if (a >= 1000) return `$${String(Number((a / 1000).toFixed(1)))} billion`;
  return `$${num(a)} million`;
}
export const millions = (v) => `$${num(Math.abs(v))}M`;

const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
export const word = (n) => WORDS[n] ?? String(n);

const asDate = (iso) => new Date(`${String(iso).slice(0, 10)}T00:00:00Z`);
export function day(iso, withYear = true) {
  const o = { month: 'short', day: 'numeric', timeZone: 'UTC' };
  if (withYear) o.year = 'numeric';
  return asDate(iso).toLocaleDateString('en-US', o);
}
export const time = (iso) => asDate(iso).getTime();
// Whole months between two dates, rounded to the nearer month.
export function monthsBetween(a, b) {
  const x = asDate(a), y = asDate(b);
  const whole = (y.getUTCFullYear() - x.getUTCFullYear()) * MONTHS_PER_YEAR + y.getUTCMonth() - x.getUTCMonth();
  const daysIn = new Date(Date.UTC(y.getUTCFullYear(), y.getUTCMonth() + 1, 0)).getUTCDate();
  return Math.round(whole + (y.getUTCDate() - x.getUTCDate()) / daysIn);
}

export const mid = (v) => (v.low + v.high) / 2;
export const linear = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);

// Round tick values inside [lo, hi], roughly `count` of them.
export function ticks(lo, hi, count) {
  const raw = (hi - lo) / Math.max(count, 1);
  const mag = 10 ** Math.floor(Math.log10(raw || 1));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((x) => x >= raw) || mag;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(Number(v.toFixed(6)));
  return out;
}

export function link(url, label, cls) {
  return h('a', { href: url, target: '_blank', rel: 'noopener', class: cls, title: `Open the SEC filing: ${url}` }, label);
}

// SVG link with a native hover tooltip; click and Enter open the filing.
export function svgLink(url, tip, ...kids) {
  return s('a', { href: url, target: '_blank', rel: 'noopener', 'aria-label': tip }, s('title', { text: tip }), ...kids);
}

// Wrap a label into lines of at most `max` characters for SVG text.
export function wrap(text, max) {
  const lines = [];
  for (const w of String(text).split(/\s+/)) {
    const last = lines[lines.length - 1];
    if (last !== undefined && (last + ' ' + w).length <= max) lines[lines.length - 1] = `${last} ${w}`;
    else lines.push(w);
  }
  return lines;
}

export const NAMES = { LMT: 'Lockheed Martin', NOC: 'Northrop Grumman', RTX: 'RTX', LHX: 'L3Harris', GD: 'General Dynamics', BA: 'Boeing' };
export const SHORT = { LMT: 'Lockheed', NOC: 'Northrop', RTX: 'RTX', LHX: 'L3Harris' };
export const ACCOUNTS = { Sales: 'Sales', SegmentOP: 'Segment profit', EPS: 'EPS', FCF: 'Free cash flow' };
export const STAGES = { Plan: 'Plan', Fcst_Q1: 'Q1 update', Fcst_Q2: 'Q2 update', Fcst_Q3: 'Q3 update', Actual: 'Actual' };
export const QUARTERS = { Q1: 'first-quarter', Q2: 'second-quarter', Q3: 'third-quarter', Q4: 'fourth-quarter', FY: 'full-year' };

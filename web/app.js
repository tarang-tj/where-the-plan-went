// Entry: load data.json, hold the selection, wire selectors, render every section.
import { h, ACCOUNTS, NAMES } from './js/util.js';
import { renderHero } from './js/walk.js';
import { renderBridge } from './js/bridge.js';
import { renderPattern, renderErrors } from './js/pattern.js';
import { renderCube } from './js/cube.js';
import { renderProgram } from './js/program.js';
import { renderMethod } from './js/method.js';

const DEFAULT = { ticker: 'LMT', year: 2025, account: 'SegmentOP' };
const key = (t, y, a) => `${t}|${y}|${a}`;
const uniq = (xs) => [...new Set(xs)];
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

async function load() {
  const res = await fetch('data.json');
  if (!res.ok) throw new Error(`data.json: HTTP ${res.status}`);
  return res.json();
}

// One walk per company-year-account: prefer plan and actual both present, then the most releases.
function pickWalks(walks) {
  const score = (w) => {
    const sc = w.vintages.map((v) => v.scenario);
    return (sc.includes('Plan') && sc.includes('Actual') ? 100 : 0) + sc.length;
  };
  const out = new Map();
  for (const w of walks) {
    const k = key(w.ticker, w.fiscal_year, w.account);
    if (!out.has(k) || score(w) > score(out.get(k))) out.set(k, w);
  }
  return out;
}

function start(data) {
  const picked = pickWalks(data.walks);
  const all = [...picked.values()];
  const state = { ...DEFAULT };
  const sel = { ticker: document.getElementById('pick-ticker'), year: document.getElementById('pick-year'),
    account: document.getElementById('pick-account') };

  function setOptions(node, values, current, label) {
    node.replaceChildren(...values.map((v) => h('option', { value: v, selected: String(v) === String(current) }, label(v))));
  }

  function sync() {
    const tickers = uniq(all.map((w) => w.ticker)).sort();
    if (!tickers.includes(state.ticker)) state.ticker = tickers[0];
    const years = uniq(all.filter((w) => w.ticker === state.ticker).map((w) => w.fiscal_year)).sort((a, b) => b - a);
    if (!years.includes(state.year)) {
      state.year = years.reduce((best, y) => (Math.abs(y - state.year) < Math.abs(best - state.year) ? y : best), years[0]);
    }
    const accts = Object.keys(ACCOUNTS).filter((a) => picked.has(key(state.ticker, state.year, a)));
    if (!accts.includes(state.account)) state.account = accts[0];
    setOptions(sel.ticker, tickers, state.ticker, (t) => `${NAMES[t] ?? t} (${t})`);
    setOptions(sel.year, years, state.year, String);
    setOptions(sel.account, accts, state.account, (a) => ACCOUNTS[a]);
  }

  function drawSized() {
    renderHero(picked.get(key(state.ticker, state.year, state.account)));
    renderBridge(data, state.ticker, state.year);
    renderProgram(data);
  }

  function render() {
    sync();
    drawSized();
    renderCube(data, picked, state, select);
    document.querySelectorAll('#pattern-chart .prow[data-key]').forEach((b) => {
      b.classList.toggle('sel', b.dataset.key === `${state.ticker}-${state.year}` && state.account === 'SegmentOP');
    });
  }

  function select(ticker, year, account) {
    Object.assign(state, { ticker, year, account });
    render();
    document.getElementById('hero').scrollIntoView({ behavior: reduceMotion.matches ? 'auto' : 'smooth' });
    sel.ticker.focus({ preventScroll: true });
  }

  sel.ticker.addEventListener('change', () => { state.ticker = sel.ticker.value; render(); });
  sel.year.addEventListener('change', () => { state.year = Number(sel.year.value); render(); });
  sel.account.addEventListener('change', () => { state.account = sel.account.value; render(); });

  renderPattern(data, select);
  renderErrors(data);
  renderMethod(data);
  render();

  let lastWidth = window.innerWidth, timer = 0;
  window.addEventListener('resize', () => {
    if (window.innerWidth === lastWidth) return;
    lastWidth = window.innerWidth;
    clearTimeout(timer);
    timer = setTimeout(drawSized, 120);
  });
  document.body.dataset.ready = 'true';
}

load().then(start).catch((err) => {
  document.getElementById('hero-h').textContent = 'The data did not load. Serve this folder over HTTP and reload.';
  console.error(err);
});

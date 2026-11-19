// Entry: load data.json, hold the selection, wire selectors, render every section.
import { h, ACCOUNTS, NAMES, measureId, measureLabel } from './js/util.js';
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

// Default walk per company-year-account when several measures exist: plan and actual both present, then most releases.
const score = (w) => {
  const sc = w.vintages.map((v) => v.scenario);
  return (sc.includes('Plan') && sc.includes('Actual') ? 100 : 0) + sc.length;
};

function start(data) {
  const all = data.walks;
  const state = { ...DEFAULT, measure: '' };
  const sel = { ticker: document.getElementById('pick-ticker'), year: document.getElementById('pick-year'),
    account: document.getElementById('pick-account'), measure: document.getElementById('pick-measure') };
  const options = () => all.filter((w) => key(w.ticker, w.fiscal_year, w.account) === key(state.ticker, state.year, state.account))
    .sort((a, b) => score(b) - score(a));
  const current = () => options().find((w) => measureId(w) === state.measure);

  function setOptions(node, values, now, label) {
    node.replaceChildren(...values.map((v) => h('option', { value: v, selected: String(v) === String(now) }, label(v))));
  }

  function sync() {
    const tickers = uniq(all.map((w) => w.ticker)).sort();
    if (!tickers.includes(state.ticker)) state.ticker = tickers[0];
    const years = uniq(all.filter((w) => w.ticker === state.ticker).map((w) => w.fiscal_year)).sort((a, b) => b - a);
    if (!years.includes(state.year)) {
      state.year = years.reduce((best, y) => (Math.abs(y - state.year) < Math.abs(best - state.year) ? y : best), years[0]);
    }
    const accts = Object.keys(ACCOUNTS).filter((a) => all.some((w) => key(w.ticker, w.fiscal_year, w.account) === key(state.ticker, state.year, a)));
    if (!accts.includes(state.account)) state.account = accts[0];
    const ms = options();
    if (!ms.some((w) => measureId(w) === state.measure)) state.measure = measureId(ms[0]);
    setOptions(sel.ticker, tickers, state.ticker, (t) => `${NAMES[t] ?? t} (${t})`);
    setOptions(sel.year, years, state.year, String);
    setOptions(sel.account, accts, state.account, (a) => ACCOUNTS[a]);
    setOptions(sel.measure, ms.map(measureId), state.measure, (id) => measureLabel(ms.find((w) => measureId(w) === id)));
    sel.measure.disabled = ms.length < 2;
  }

  function drawSized() {
    renderHero(current());
    renderBridge(data, state.ticker, state.year);
    renderProgram(data);
  }

  function render() {
    sync();
    drawSized();
    renderCube(data, all, state, select);
    document.querySelectorAll('#pattern-chart .prow[data-key]').forEach((b) => {
      b.classList.toggle('sel', b.dataset.key === `${state.ticker}-${state.year}` && state.account === 'SegmentOP');
    });
  }

  function select(ticker, year, account, measure = state.measure) {
    Object.assign(state, { ticker, year, account, measure });
    render();
    document.getElementById('hero').scrollIntoView({ behavior: reduceMotion.matches ? 'auto' : 'smooth' });
    sel.ticker.focus({ preventScroll: true });
  }

  sel.ticker.addEventListener('change', () => { state.ticker = sel.ticker.value; render(); });
  sel.year.addEventListener('change', () => { state.year = Number(sel.year.value); render(); });
  sel.account.addEventListener('change', () => { state.account = sel.account.value; render(); });
  sel.measure.addEventListener('change', () => { state.measure = sel.measure.value; render(); });

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

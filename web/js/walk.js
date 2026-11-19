// Section 1: the forecast walk. Headline, range bars per release, actual dot, callout at the biggest move.
import {
  h, s, fill, num, dollars, millions, word, day, time, monthsBetween, mid, linear, ticks, digits,
  svgLink, link, STAGES, SHORT, NAMES, QUARTERS,
} from './util.js';

const plural = (x, n) => (n > 1 ? `${x}${x.endsWith('s') ? 'es' : 's'}` : x);
const value = (v) => (v.scenario === 'Actual' ? v.low : mid(v));
const rangeText = (v, d) => (v.low === v.high ? num(v.low, d) : `${num(v.low, d)}–${num(v.high, d)}`);

// Find the largest single-release drop of the midpoint (or the largest rise when nothing fell).
export function story(w) {
  const vs = w.vintages, vals = vs.map(value), u = w.unit;
  let drop = 0, rise = 0;
  for (let i = 1; i < vals.length; i++) {
    const d = vals[i] - vals[i - 1];
    if (d < 0 && (!drop || d < vals[drop] - vals[drop - 1])) drop = i;
    if (d > 0 && (!rise || d > vals[rise] - vals[rise - 1])) rise = i;
  }
  const subject = vs[0].scenario === 'Plan' ? 'The plan' : 'Guidance';
  const hasActual = vs[vs.length - 1].scenario === 'Actual';
  const idx = drop || rise;
  if (!idx) {
    const text = hasActual
      ? `${subject} never moved, and the result matched it at ${dollars(vals[0], u)}.`
      : `${subject} held at ${dollars(vals[0], u)} at every release.`;
    return { text, idx: 0, kind: 'flat' };
  }
  const amt = dollars(vals[idx] - vals[idx - 1], u);
  const atActual = vs[idx].scenario === 'Actual';
  const held = vals.slice(0, idx).every((x) => x === vals[0]);
  let text;
  if (drop && atActual) {
    text = held ? `${subject} held all year, then the result came in ${amt} below it.`
      : `The result came in ${amt} below the last forecast.`;
  } else if (drop && held && idx > 1) {
    const m = monthsBetween(vs[0].date, vs[idx].date);
    text = `${subject} held for ${m === 1 ? 'one month' : `${word(m)} months`}, then fell ${amt} in one release.`;
  } else if (drop) {
    text = idx === 1 ? `${subject} fell ${amt} at the first update.`
      : `The biggest cut came in the ${STAGES[vs[idx].scenario]}: ${amt} off the midpoint.`;
  } else {
    text = atActual ? `${subject} never fell, and the result beat the last forecast by ${amt}.`
      : `${subject} never fell. Its biggest step was up ${amt}, in the ${STAGES[vs[idx].scenario]}.`;
  }
  return { text, idx, kind: drop ? 'drop' : 'rise' };
}

function calloutBody(w, st) {
  const vs = w.vintages, d = digits(w.unit);
  const parts = [];
  if (st.idx) {
    const from = value(vs[st.idx - 1]), to = value(vs[st.idx]);
    parts.push(h('b', { text: `${day(vs[st.idx].date)}.` }), ` Midpoint ${num(from, d)} to ${num(to, d)}. `);
  }
  if (w.account !== 'SegmentOP') {
    parts.push('Program charges are tied to segment profit, so none are listed for this measure.');
  } else if (!w.charges.length) {
    parts.push(`No named program charge is recorded for ${w.ticker} in ${w.fiscal_year}.`);
  } else {
    const kinds = new Set(w.charges.map((c) => `${QUARTERS[c.quarter] ?? c.quarter} ${c.basis}`));
    const shared = kinds.size === 1 ? [...kinds][0] : '';
    const many = w.charges.length > 1;
    parts.push(`Named program charge${many ? 's' : ''} in ${w.fiscal_year}`
      + `${shared ? (many ? `, all ${plural(shared, w.charges.length)}` : ` (${shared})`) : ''}: `);
    w.charges.forEach((c, i) => {
      parts.push(link(c.url, `${millions(c.amount)} on ${c.program}`, 'charge'));
      if (!shared) parts.push(` (${QUARTERS[c.quarter] ?? c.quarter} ${c.basis})`);
      parts.push(i === w.charges.length - 1 ? '.' : ', ');
    });
  }
  return parts;
}

export function renderHero(w) {
  const st = story(w);
  const hero = document.getElementById('hero');
  hero.dataset.key = `${w.ticker}-${w.fiscal_year}-${w.account}`;
  fill('hero-kicker', `Where the plan went · ${w.ticker} ${w.fiscal_year}`);
  fill('hero-h', st.text);
  const done = w.vintages[w.vintages.length - 1].scenario === 'Actual';
  fill('hero-sub', `${SHORT[w.ticker] ?? NAMES[w.ticker]}'s guidance for ${w.fiscal_year} ${w.measure} (${w.basis}`
    + `${w.unit === 'USD_M' ? ', $ millions' : ', $ per share'}), release by release, `
    + (done ? 'against what it reported.' : 'before the result is out.'));
  drawWalk(w, st);
}

export function drawWalk(w, st) {
  const stage = fill('walk');
  const W = stage.clientWidth, narrow = W < 640, vs = w.vintages, n = vs.length, d = digits(w.unit);
  const left = narrow ? 50 : 64, right = W - (narrow ? 8 : 24), top = 44, H = narrow ? 300 : 440, bottom = H - 50;
  const lows = vs.map((v) => v.low), highs = vs.map((v) => v.high);
  let lo = Math.min(...lows), hi = Math.max(...highs);
  const pad = (hi - lo || Math.abs(hi) || 1) * 0.18;
  lo -= pad; hi += pad;
  const y = linear(lo, hi, bottom, top);
  const bw = Math.min(92, ((right - left) / n) * (narrow ? 0.62 : 0.55));
  const t0 = time(vs[0].date), t1 = time(vs[n - 1].date);
  const x = n === 1 ? () => (left + right) / 2 : linear(t0, t1, left + bw / 2 + 6, right - bw / 2);
  const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img',
    'aria-label': `${w.ticker} ${w.fiscal_year} ${w.account} guidance by release. ${st.text}` });
  const boxes = [];
  for (const tv of ticks(lo, hi, narrow ? 4 : 5)) {
    svg.append(s('line', { x1: left, x2: right, y1: y(tv), y2: y(tv), class: 'grid' }),
      s('text', { x: left - 8, y: y(tv) + 4, 'text-anchor': 'end', class: 'ax', text: num(tv, d) }));
  }
  vs.forEach((v, i) => {
    const cx = x(time(v.date)), tip = `${STAGES[v.scenario]}, ${day(v.date)}: ${rangeText(v, d)}. Click to open the filing.`;
    if (v.scenario === 'Actual') {
      svg.append(svgLink(v.url, tip, s('circle', { cx, cy: y(v.low), r: 8, class: 'dot' }),
        s('text', { x: cx, y: y(v.low) - 16, 'text-anchor': 'middle', class: 'big', text: num(v.low, d) })));
      boxes.push([cx - 30, y(v.low) - 32, cx + 30, y(v.low) + 9]);
    } else {
      const label = narrow && v.low !== v.high
        ? [s('tspan', { x: cx, dy: '-1.2em', text: `${num(v.low, d)}–` }), s('tspan', { x: cx, dy: '1.2em', text: num(v.high, d) })]
        : [rangeText(v, d)];
      svg.append(svgLink(v.url, tip,
        s('rect', { x: cx - bw / 2, y: y(v.high), width: bw, height: Math.max(5, y(v.low) - y(v.high)), rx: 3, class: 'bar' }),
        s('text', { x: cx, y: y(v.high) - 9, 'text-anchor': 'middle', class: 'rng' }, ...label)));
      boxes.push([cx - bw / 2 - 12, y(v.high) - (narrow ? 40 : 26), cx + bw / 2 + 12, y(v.low) + 5]);
    }
    const stage = narrow ? STAGES[v.scenario].replace(' update', '') : STAGES[v.scenario];
    const when = i === 0 || i === n - 1 || !narrow ? day(v.date, i === 0 || i === n - 1) : day(v.date, false);
    svg.append(s('text', { x: cx, y: bottom + 22, 'text-anchor': 'middle', class: 'xl' },
      s('tspan', { x: cx, text: narrow ? day(v.date, false) : when }), s('tspan', { x: cx, dy: '1.3em', text: stage })));
  });
  if (st.idx) {
    const a = vs[st.idx - 1], b = vs[st.idx], xa = x(time(a.date)) + bw / 2, xb = x(time(b.date)) - (b.scenario === 'Actual' ? 10 : bw / 2);
    const ya = y(value(a)), yb = y(value(b)), k = (xb - xa) / 2;
    svg.append(s('path', { d: `M${xa},${ya} C${xa + k},${ya} ${xb - k},${yb} ${xb},${yb}`, class: 'cliff' }));
  }
  stage.append(svg);
  placeCallout(stage, w, st, { x, y, bw, top, bottom, W, narrow, boxes });
}

// Put the callout in the empty corner beside the biggest move; fall back to below the chart on overlap.
function placeCallout(stage, w, st, g) {
  const call = h('div', { class: 'call', id: 'callout' }, ...calloutBody(w, st));
  stage.append(call);
  if (g.narrow || !st.idx) return;
  const vs = w.vintages, cx = g.x(time(vs[st.idx].date)), right = st.idx < vs.length - 1;
  const width = Math.min(380, g.W * 0.4);
  call.classList.add('float');
  call.style.width = `${width}px`;
  const ht = call.offsetHeight, upper = (st.kind === 'drop') === right;
  let x0 = right ? cx + g.bw / 2 + 18 : cx - g.bw / 2 - 18 - width;
  x0 = Math.max(g.x(time(vs[0].date)) - g.bw / 2, Math.min(x0, g.W - width));
  const y0 = upper ? g.top - 8 : g.bottom - ht - 6;
  const hit = g.boxes.some(([a, b, c, d]) => a < x0 + width && c > x0 && b < y0 + ht && d > y0);
  if (hit) { call.classList.remove('float'); call.style.width = ''; return; }
  call.style.left = `${x0}px`;
  call.style.top = `${y0}px`;
}

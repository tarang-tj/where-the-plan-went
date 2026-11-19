// Section 2: plan-to-actual bridge for segment profit, each named charge as its own step.
import { h, s, fill, num, signed, dollars, millions, linear, wrap, svgLink, link, NAMES, SHORT, MINUS } from './util.js';

export function bridgeSteps(b, charges) {
  const mine = charges.filter((c) => c.ticker === b.ticker && c.fiscal_year === b.fiscal_year);
  const total = mine.reduce((t, c) => t + Number(c.amount), 0);
  const steps = [{ label: `${b.fiscal_year} plan`, v: b.plan_op, kind: 'total' },
    { label: b.volume >= 0 ? 'Higher sales' : 'Lower sales', v: b.volume, kind: 'delta' }];
  if (mine.length && Math.abs(total + b.named_charges) < 0.5) {
    for (const c of mine) steps.push({ label: c.program, v: -Number(c.amount), kind: 'charge', url: c.url, quote: c.quote });
  } else if (b.named_charges) {
    steps.push({ label: 'Named charges', v: b.named_charges, kind: 'charge' });
  }
  steps.push({ label: 'Everything else', v: b.other, kind: 'delta' },
    { label: `${b.fiscal_year} actual`, v: b.actual_op, kind: 'total' });
  let run = 0;
  for (const st of steps) {
    if (st.kind === 'total') { st.a = 0; st.z = st.v; run = st.v; } else { st.a = run; st.z = run + st.v; run = st.z; }
  }
  return { steps, mine };
}

const valueText = (st) => (st.kind === 'total' ? num(st.v) : signed(st.v));
const tip = (st) => `${st.label}: ${valueText(st)} $M. ${st.quote ? `"${st.quote}" ` : ''}Click to open the filing.`;

function piece(st, shape, text) {
  return st.url ? svgLink(st.url, tip(st), shape, text) : s('g', {}, s('title', { text: `${st.label}: ${valueText(st)} $M` }), shape, text);
}

function domain(steps) {
  const lv = steps.flatMap((st) => (st.kind === 'total' ? [st.v] : [st.a, st.z]));
  const lo = Math.min(...lv), hi = Math.max(...lv), span = hi - lo || hi || 1;
  return [lo - span * 0.35, hi + span * 0.08];
}

function vertical(steps, W) {
  const H = 345, top = 30, bottom = 280, slot = W / steps.length, bw = Math.min(110, slot * 0.72);
  const [lo, hi] = domain(steps), y = linear(lo, hi, bottom, top);
  const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Bridge from plan to actual' });
  steps.forEach((st, i) => {
    const x = i * slot + (slot - bw) / 2, a = st.kind === 'total' ? lo : st.a, z = st.kind === 'total' ? st.v : st.z;
    const y0 = Math.min(y(a), y(z));
    svg.append(piece(st, s('rect', { x, y: y0, width: bw, height: Math.max(2, Math.abs(y(a) - y(z))), class: `wf ${st.kind}` }),
      s('text', { x: x + bw / 2, y: y0 - 8, 'text-anchor': 'middle', class: `wv ${st.kind}`, text: valueText(st) })));
    const lines = wrap(st.label, Math.max(8, Math.floor(slot / 7)));
    svg.append(s('text', { x: x + bw / 2, y: bottom + 20, 'text-anchor': 'middle', class: 'xl' },
      ...lines.map((ln, j) => s('tspan', { x: x + bw / 2, dy: j ? '1.3em' : 0, text: ln }))));
  });
  return svg;
}

function horizontal(steps, W) {
  const row = 40, labelW = Math.min(150, W * 0.42), top = 6, H = top + steps.length * row + 6;
  const [lo, hi] = domain(steps), x = linear(lo, hi, labelW + 8, W - 52);
  const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Bridge from plan to actual' });
  steps.forEach((st, i) => {
    const yy = top + i * row, a = st.kind === 'total' ? lo : st.a, z = st.kind === 'total' ? st.v : st.z;
    const x0 = Math.min(x(a), x(z)), x1 = Math.max(x(a), x(z));
    const lines = wrap(st.label, Math.floor(labelW / 6.6)).slice(0, 2);
    svg.append(s('text', { x: 0, y: yy + (lines.length > 1 ? 14 : 22), class: 'xl left' },
      ...lines.map((ln, j) => s('tspan', { x: 0, dy: j ? '1.25em' : 0, text: ln }))));
    svg.append(piece(st, s('rect', { x: x0, y: yy + 8, width: Math.max(2, x1 - x0), height: row - 16, class: `wf ${st.kind}` }),
      s('text', { x: x1 + 4, y: yy + 24, class: `wv small ${st.kind}`, text: valueText(st) })));
  });
  return svg;
}

export function renderBridge(data, ticker, year) {
  const sec = document.getElementById('bridge');
  const b = data.bridges.find((r) => r.ticker === ticker && r.fiscal_year === year);
  sec.dataset.key = b ? `${ticker}-${year}` : `${ticker}-${year}-none`;
  if (!b) {
    const guides = data.bridges.some((r) => r.ticker === ticker);
    fill('bridge-sub', guides
      ? `There is no bridge for ${ticker} ${year}: the filings do not give both a dollar segment profit plan and a reported actual for that year.`
      : `There is no bridge for ${ticker} ${year}: ${NAMES[ticker] ?? ticker} does not guide segment profit in dollars, so there is no plan to walk from.`);
    fill('bridge-chart');
    fill('bridge-quotes');
    return;
  }
  const { steps } = bridgeSteps(b, data.charges);
  const who = SHORT[ticker] ?? ticker;
  fill('bridge-sub', `${who} planned ${dollars(b.plan_op)} of segment profit for ${year} and made ${dollars(b.actual_op)}. `
    + (b.named_charges ? `Named program charges took ${dollars(b.named_charges)}; ` : 'No named program charge hit that year; ')
    + 'sales volume and everything else make up the rest. $ millions; the axis does not start at zero.');
  const box = fill('bridge-chart');
  box.append(box.clientWidth < 640 ? horizontal(steps, box.clientWidth) : vertical(steps, box.clientWidth));
  fill('bridge-quotes', steps.filter((st) => st.quote).map((st) => h('li', {},
    h('b', { text: `${MINUS}${millions(st.v)}` }), ` “${st.quote}” `, link(st.url, 'filing', 'src'))));
}

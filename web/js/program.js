// Section 6: one SYNTHETIC fixed-price program, showing how a rising EAC becomes a reach-forward loss.
import { s, fill, num, linear, ticks } from './util.js';

function lineChart(box, { series, refs, months, periods, marker, title }) {
  const W = box.clientWidth, narrow = W < 640, H = narrow ? 230 : 260;
  const left = narrow ? 40 : 52, right = W - 10, top = 48, bottom = H - 32;
  const all = series.flatMap((x) => x.vals).concat(refs.map((r) => r.v)).filter((v) => Number.isFinite(v));
  let lo = Math.min(...all), hi = Math.max(...all);
  const pad = (hi - lo || 1) * 0.08;
  lo -= pad; hi += pad;
  const x = linear(months[0], months[months.length - 1], left, right), y = linear(lo, hi, bottom, top);
  const svg = s('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': title },
    s('text', { x: 0, y: 14, class: 'ctitle', text: title }));
  for (const tv of ticks(lo, hi, 4)) {
    svg.append(s('line', { x1: left, x2: right, y1: y(tv), y2: y(tv), class: 'grid' }),
      s('text', { x: left - 6, y: y(tv) + 4, 'text-anchor': 'end', class: 'ax', text: num(tv) }));
  }
  const every = Math.ceil(months.length / (narrow ? 3 : 6));
  months.forEach((m, i) => {
    if (i % every === 0 || i === months.length - 1) {
      const anchor = i === 0 ? 'start' : i === months.length - 1 ? 'end' : 'middle';
      svg.append(s('text', { x: x(m), y: bottom + 18, 'text-anchor': anchor, class: 'ax', text: periods[i] }));
    }
  });
  for (const r of refs) {
    svg.append(s('line', { x1: left, x2: right, y1: y(r.v), y2: y(r.v), class: r.cls }),
      s('text', { x: right, y: y(r.v) - 5, 'text-anchor': 'end', class: `rlab ${r.cls}`, text: r.label }));
  }
  for (const ser of series) {
    const d = ser.vals.map((v, i) => `${i ? 'L' : 'M'}${x(months[i]).toFixed(1)},${y(v).toFixed(1)}`).join('');
    svg.append(s('path', { d, class: `line ${ser.cls}` }));
  }
  if (marker) {
    svg.append(s('line', { x1: x(marker.m), x2: x(marker.m), y1: top, y2: bottom, class: 'mark' }),
      s('text', { x: x(marker.m) + (x(marker.m) > W * 0.7 ? -6 : 6), y: top - 8,
        'text-anchor': x(marker.m) > W * 0.7 ? 'end' : 'start', class: 'rlab mark', text: marker.label }));
  }
  box.replaceChildren(svg);
}

export function renderProgram(data) {
  const evm = data.program.evm, rr = data.program.revrec;
  const months = evm.map((r) => r.month), periods = evm.map((r) => r.period);
  const name = evm[0].program, bac = evm[0].bac, price = rr[0].price;
  const loss = rr.find((r) => r.cum_gross_profit < 0), before = rr[rr.indexOf(loss) - 1];
  const over = rr.find((r) => r.eac > price), last = rr[rr.length - 1];
  fill('program-text', `This is an illustrative synthetic program, not a real one, built to show the mechanism behind a `
    + `reach-forward loss. ${name} has a budget at completion of $${num(bac)}M and a fixed price of $${num(price)}M. `
    + `Cost performance is below plan from the first month (CPI ${num(evm[0].cpi, 2)}), so the estimate at completion (EAC) rises. `
    + (over ? `In ${over.period} the EAC reaches $${num(over.eac)}M, above the price. ` : '')
    + (loss && before ? `${over && over.period === loss.period ? 'That month' : `In ${loss.period}`} the whole expected loss `
      + 'is booked at once: cumulative gross profit goes from '
      + `$${num(before.cum_gross_profit, 1)}M to ${loss.cum_gross_profit < 0 ? '−⁠' : ''}$${num(Math.abs(loss.cum_gross_profit), 1)}M in one month. ` : '')
    + `The program finishes at ${last.cum_gross_profit < 0 ? '−⁠' : ''}$${num(Math.abs(last.cum_gross_profit), 1)}M. `
    + 'That is the same shape as the real charges above: profit looks fine until the estimate crosses the price.');
  const lossMark = loss ? { m: loss.month, label: `Loss booked ${loss.period}` } : null;
  lineChart(document.getElementById('program-eac'), {
    title: 'SYNTHETIC · EAC vs budget and price, $M', months, periods, marker: lossMark,
    series: [{ vals: evm.map((r) => r.eac_composite), cls: 'eac' }],
    refs: [{ v: bac, label: 'Budget (BAC)', cls: 'ref' }, { v: price, label: 'Price', cls: 'price' }],
  });
  lineChart(document.getElementById('program-gp'), {
    title: 'SYNTHETIC · cumulative gross profit, $M', months, periods, marker: lossMark,
    series: [{ vals: rr.map((r) => r.cum_gross_profit), cls: 'gp' }],
    refs: [{ v: 0, label: 'Break-even', cls: 'ref' }],
  });
}

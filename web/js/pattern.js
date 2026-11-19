// Sections 3 and 4: plan variance against named charges for every bridge year, and guidance error by vintage.
import { h, fill, signed, ACCOUNTS, STAGES } from './util.js';

const N = (data, key) => data.numbers[key]?.display ?? 'n/a';

export function renderPattern(data, select) {
  fill('pattern-text', `In ${N(data, 'large_misses')} of the ${N(data, 'bridge_company_years')} company-years with a dollar plan, `
    + `segment profit came in more than ${N(data, 'large_miss_threshold')} below plan, and named program charges `
    + `covered at least ${N(data, 'large_miss_min_charge_cover')} of each of those misses. In the other years, no `
    + 'company-year finished more than $' + N(data, 'other_years_worst_miss_abs') + ' million below plan.');
  const rows = data.bridges.map((b) => ({ ...b, miss: b.actual_op - b.plan_op }))
    .sort((a, b) => a.miss - b.miss || b.fiscal_year - a.fiscal_year);
  const top = Math.max(...rows.flatMap((r) => [Math.abs(r.miss), Math.abs(r.named_charges)])) || 1;
  const bar = (v, cls) => h('span', { class: `pbar ${cls}`, style: `width:${(Math.abs(v) / top) * 100}%` });
  fill('pattern-chart',
    h('div', { class: 'prow head', 'aria-hidden': 'true' }, h('span', { text: 'Company-year' }),
      h('span', { text: 'Actual minus plan, $M' }), h('span', { text: 'Named charges, $M' })),
    rows.map((r) => h('button', {
      type: 'button', class: 'prow', 'data-key': `${r.ticker}-${r.fiscal_year}`,
      'aria-label': `${r.ticker} ${r.fiscal_year}: variance ${signed(r.miss)}, named charges ${signed(r.named_charges)}. Show this year above.`,
      onclick: () => select(r.ticker, r.fiscal_year, 'SegmentOP'),
    }, h('span', { class: 'mono', text: `${r.ticker} ${r.fiscal_year}` }),
    h('span', { class: 'pcell' }, bar(r.miss, r.miss < 0 ? 'neg' : 'pos'), h('span', { class: 'mono', text: signed(r.miss) })),
    h('span', { class: 'pcell' }, bar(r.named_charges, 'charge'), h('span', { class: 'mono', text: signed(r.named_charges) })))));
}

const VINTAGES = ['Plan', 'Fcst_Q1', 'Fcst_Q2', 'Fcst_Q3'];

export function renderErrors(data) {
  const accts = Object.keys(ACCOUNTS).filter((a) => data.numbers[`err_${a}_Plan_median_abs`]);
  const v = (a, sc, m) => data.numbers[`err_${a}_${sc}_${m}`];
  const lastBeat = accts.map((a) => v(a, 'Fcst_Q3', 'beat_share')).filter(Boolean);
  const allOver = lastBeat.length && lastBeat.every((x) => x.value > 0.5);
  const inside = accts.flatMap((a) => VINTAGES.map((sc) => v(a, sc, 'inside_share'))).filter(Boolean)
    .sort((x, y) => x.value - y.value);
  const shrinks = accts.every((a) => v(a, 'Fcst_Q3', 'median_abs')?.value < v(a, 'Plan', 'median_abs').value);
  fill('errors-text',
    `${allOver ? 'Late in the year, every measure beats its guidance more often than not. ' : ''}`
    + 'At the third-quarter update, the result beat the guidance midpoint for '
    + accts.map((a) => `${ACCOUNTS[a].toLowerCase()} ${v(a, 'Fcst_Q3', 'beat_share')?.display ?? 'n/a'}`).join(', ')
    + ' of the time. The printed range is narrow: results landed inside it between '
    + `${inside[0]?.display ?? 'n/a'} and ${inside[inside.length - 1]?.display ?? 'n/a'} of the time, depending on measure and release. `
    + (shrinks ? 'For every measure, the median miss is smaller at the third-quarter update than at plan.' : ''));
  fill('errors-grid', accts.map((a) => h('figure', { class: 'card' },
    h('figcaption', {}, h('b', { text: ACCOUNTS[a] }), ` · ${N(data, `err_${a}_Plan_n`)} plans scored`),
    h('table', { class: 'mini' },
      h('thead', {}, h('tr', {}, h('th', { text: 'Release' }), h('th', { text: 'Median miss' }),
        h('th', { text: 'Beat midpoint' }), h('th', { text: 'Inside range' }))),
      h('tbody', {}, VINTAGES.filter((sc) => v(a, sc, 'median_abs')).map((sc) => h('tr', {},
        h('td', { text: STAGES[sc] }), h('td', { text: v(a, sc, 'median_abs').display }),
        h('td', { text: v(a, sc, 'beat_share').display }), h('td', { text: v(a, sc, 'inside_share').display }))))))));
}

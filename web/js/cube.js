// Section 5: plan vs actual for every walk (company-year-measure) of the selected account; a row click drives sections 1 and 2.
import { h, fill, num, signed, digits, mid, ACCOUNTS, measureId, measureLabel } from './util.js';

const vintage = (w, sc) => w.vintages.find((v) => v.scenario === sc);

export function renderCube(data, walks, state, select) {
  const rows = walks.filter((w) => w.account === state.account)
    .sort((a, b) => b.fiscal_year - a.fiscal_year || a.ticker.localeCompare(b.ticker) || measureId(a).localeCompare(measureId(b)));
  const op = state.account === 'SegmentOP';
  fill('cube-kicker', `Planning cube · Account = ${state.account} · ${rows[0]?.unit === 'USD_per_share' ? '$ per share' : '$M'}`);
  fill('cube-h', `${ACCOUNTS[state.account]}: plan vs actual, every company-year`);
  const head = ['Entity · FY', 'Measure', 'Plan', 'Actual', 'Variance', 'Variance %'].concat(op ? ['Named charges'] : []);
  fill('cube-table',
    h('caption', { class: 'sr', text: `${ACCOUNTS[state.account]} plan and actual by company-year and measure. Select a row to show it above.` }),
    h('thead', {}, h('tr', {}, head.map((t, i) => h('th', { scope: 'col', class: i > 4 ? 'wide' : null, text: t })))),
    h('tbody', {}, rows.map((w) => {
      // Plan, actual and variance all come from this one walk, so they share a basis and measure.
      const d = digits(w.unit), plan = vintage(w, 'Plan'), act = vintage(w, 'Actual');
      const p = plan ? mid(plan) : null, a = act ? act.low : null, v = p !== null && a !== null ? a - p : null;
      const br = op ? data.bridges.find((b) => b.ticker === w.ticker && b.fiscal_year === w.fiscal_year) : null;
      const on = w.ticker === state.ticker && w.fiscal_year === state.year && measureId(w) === state.measure;
      const go = () => select(w.ticker, w.fiscal_year, w.account, measureId(w));
      return h('tr', { class: on ? 'sel' : null, onclick: go, 'data-key': `${w.ticker}-${w.fiscal_year}` },
        h('th', { scope: 'row' }, h('button', { type: 'button', class: 'rowbtn', 'aria-pressed': on ? 'true' : 'false',
          onclick: (e) => { e.stopPropagation(); go(); }, text: `${w.ticker} ${w.fiscal_year}` })),
        h('td', { class: 'meas', text: measureLabel(w) }),
        h('td', { class: 'plan', text: p === null ? 'n/a' : num(p, d) }),
        h('td', { class: 'actual', text: a === null ? 'n/a' : num(a, d) }),
        h('td', { class: v === null ? null : v < 0 ? 'neg' : 'pos', text: v === null ? 'n/a' : signed(v, d) }),
        h('td', { class: 'wide', text: v === null ? 'n/a' : `${signed((v / Math.abs(p)) * 100, 1)}%` }),
        op ? h('td', { class: 'wide neg', text: br ? signed(br.named_charges) : 'n/a' }) : null);
    })));
}

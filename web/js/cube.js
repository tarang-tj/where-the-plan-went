// Section 5: plan vs actual for every company-year of the selected account; a row click drives sections 1 and 2.
import { h, fill, num, signed, digits, mid, ACCOUNTS } from './util.js';

const vintage = (w, sc) => w.vintages.find((v) => v.scenario === sc);

export function renderCube(data, picked, state, select) {
  const rows = [...picked.values()].filter((w) => w.account === state.account)
    .sort((a, b) => b.fiscal_year - a.fiscal_year || a.ticker.localeCompare(b.ticker));
  const op = state.account === 'SegmentOP';
  fill('cube-kicker', `Planning cube · Account = ${state.account} · ${rows[0]?.unit === 'USD_per_share' ? '$ per share' : '$M'}`);
  fill('cube-h', `${ACCOUNTS[state.account]}: plan vs actual, every company-year`);
  const head = ['Entity · FY', 'Plan', 'Actual', 'Variance', 'Variance %'].concat(op ? ['Named charges'] : []);
  fill('cube-table',
    h('caption', { class: 'sr', text: `${ACCOUNTS[state.account]} plan and actual by company-year. Select a row to show it above.` }),
    h('thead', {}, h('tr', {}, head.map((t, i) => h('th', { scope: 'col', class: i > 3 ? 'wide' : null, text: t })))),
    h('tbody', {}, rows.map((w) => {
      const d = digits(w.unit), plan = vintage(w, 'Plan'), act = vintage(w, 'Actual');
      const p = plan ? mid(plan) : null, a = act ? act.low : null, v = p !== null && a !== null ? a - p : null;
      const br = op ? data.bridges.find((b) => b.ticker === w.ticker && b.fiscal_year === w.fiscal_year) : null;
      const on = w.ticker === state.ticker && w.fiscal_year === state.year;
      const go = () => select(w.ticker, w.fiscal_year, w.account);
      return h('tr', { class: on ? 'sel' : null, onclick: go },
        h('th', { scope: 'row' }, h('button', { type: 'button', class: 'rowbtn', 'aria-pressed': on ? 'true' : 'false',
          onclick: (e) => { e.stopPropagation(); go(); }, text: `${w.ticker} ${w.fiscal_year}` })),
        h('td', { text: p === null ? 'n/a' : num(p, d) }),
        h('td', { text: a === null ? 'n/a' : num(a, d) }),
        h('td', { class: v === null ? null : v < 0 ? 'neg' : 'pos', text: v === null ? 'n/a' : signed(v, d) }),
        h('td', { class: 'wide', text: v === null ? 'n/a' : `${signed((v / Math.abs(p)) * 100, 1)}%` }),
        op ? h('td', { class: 'wide neg', text: br ? signed(br.named_charges) : 'n/a' }) : null);
    })));
}

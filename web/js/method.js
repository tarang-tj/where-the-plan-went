// Section 7: method, gates, coverage gaps, counts from data.meta, crosswalk summary.
import { h, fill, num, NAMES } from './util.js';

const REPO = 'https://github.com/tarang-tj/where-the-plan-went';

// Years inside a company's covered span that have no guidance walk at all.
function gapYears(walks, ticker) {
  const ys = new Set(walks.filter((w) => w.ticker === ticker).map((w) => w.fiscal_year));
  if (!ys.size) return [];
  const lo = Math.min(...ys), hi = Math.max(...ys), out = [];
  for (let y = lo; y <= hi; y++) if (!ys.has(y)) out.push(y);
  return out;
}

export function renderMethod(data) {
  const m = data.meta, lhx = gapYears(data.walks, 'LHX');
  const lhxSpan = lhx.length ? (lhx.length > 1 ? `${lhx[0]} to ${lhx[lhx.length - 1]}` : String(lhx[0])) : '';
  fill('method-body',
    h('h3', { text: 'Pipeline' }),
    h('p', {}, `SEC filings (earnings-release exhibits and 10-Ks) feed a Databricks medallion: bronze as filed, silver typed and keyed, `
      + `gold for analysis. The same SQL runs locally on DuckDB, and a parity check requires both engines to agree. This build read `
      + `${num(m.filings)} filings and ${num(m.facts)} XBRL facts, plus ${num(m.curated_rows)} hand-curated rows `
      + `(guidance, EAC adjustments, program charges), input hash `, h('code', { text: m.inputs_sha256 }), '.'),
    h('h3', { text: 'Gates' }),
    h('ul', {},
      h('li', {}, h('b', { text: 'Quote check. ' }), 'Every hand-entered number cites a sentence that must appear word for word in the cached filing, with the number inside it.'),
      h('li', {}, h('b', { text: 'Reconcile. ' }), 'Segment sales sum to the consolidated figure, year-end release actuals match the 10-K XBRL, and when an update prints the prior outlook beside the new one, that prior must equal the vintage recorded before it.'),
      h('li', {}, h('b', { text: 'Parity. ' }), 'Gold tables built on Databricks and on DuckDB must match.')),
    h('h3', { text: 'Coverage gaps' }),
    h('ul', {},
      lhxSpan ? h('li', {}, `L3Harris ${lhxSpan}: guidance appears only as images in investor letters, so there is no text to quote and no row.`) : null,
      h('li', {}, `${NAMES.GD} and ${NAMES.BA} give no numeric guidance in their earnings releases. Boeing's program charges are recorded; there is no plan to compare them with.`),
      h('li', {}, 'Nothing is estimated or carried forward. If a filing does not print a number, the row does not exist.')),
    h('h3', { text: 'How this maps to enterprise planning tools' }),
    h('p', { class: 'note' }, 'Based on the vendors’ public documentation, not on experience operating these systems.'),
    h('table', { class: 'xwalk' },
      h('thead', {}, h('tr', {}, h('th', { text: 'Here' }), h('th', { text: 'Maps to' }))),
      h('tbody', {},
        h('tr', {}, h('td', { text: 'Plan-versus-actual cube: entity, scenario, account, year, program' }),
          h('td', { text: 'OneStream cube dimensions (Entity, Scenario, Account, Time, User Defined)' })),
        h('tr', {}, h('td', { text: 'Synthetic program ledger and indirect rates' }),
          h('td', { text: 'Deltek Costpoint projects, organizations, accounts and indirect rate computation' })),
        h('tr', {}, h('td', { text: 'Percent-complete revenue, catch-up and loss provision' }),
          h('td', { text: 'Dynamics 365 revenue recognition on fixed-price projects; financial dimensions' })))),
    h('p', {}, 'Code, data and every gate: ', h('a', { href: REPO, rel: 'noopener', text: 'github.com/tarang-tj/where-the-plan-went' }), '.'));
}

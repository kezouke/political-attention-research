'use strict';

const data = window.CRISIS_DATA;
const $ = (selector) => document.querySelector(selector);
const languageFromUrl = () => new URLSearchParams(location.search).get('lang') === 'ru' ? 'ru' : 'en';
let lang = languageFromUrl();
let dismissActiveTooltip;
const t = (en, ru) => lang === 'ru' ? ru : en;
const iso2 = {
  ALB: 'AL', ARG: 'AR', AUS: 'AU', AUT: 'AT', BEL: 'BE', BOL: 'BO', BRA: 'BR',
  BGR: 'BG', CAN: 'CA', CHL: 'CL', COL: 'CO', CZE: 'CZ', DNK: 'DK', ECU: 'EC',
  SLV: 'SV', EST: 'EE', FIN: 'FI', FRA: 'FR', DEU: 'DE', GRC: 'GR', HUN: 'HU',
  ISL: 'IS', IND: 'IN', IDN: 'ID', IRL: 'IE', ITA: 'IT', JPN: 'JP', LVA: 'LV',
  LUX: 'LU', MEX: 'MX', NLD: 'NL', NZL: 'NZ', NOR: 'NO', PAK: 'PK', PER: 'PE',
  PHL: 'PH', POL: 'PL', PRT: 'PT', ROU: 'RO', RUS: 'RU', SRB: 'RS', SVK: 'SK',
  ZAF: 'ZA', ESP: 'ES', SWE: 'SE', CHE: 'CH', THA: 'TH', TUR: 'TR', GBR: 'GB',
  USA: 'US', VEN: 'VE', ZMB: 'ZM',
};
const issueNames = {
  corruption: ['Corruption', 'Коррупция'],
  health: ['Health care', 'Здравоохранение'],
  economy_strict: ['Economic problems, narrow coding', 'Экономические проблемы, узкая кодировка'],
};
const crisisNames = {
  banking: ['Banking crisis', 'Банковский кризис'],
  recession: ['Recession', 'Рецессия'],
};
const priceStatus = {
  not_classified: ['Outside The PopuList', 'Вне охвата The PopuList'],
  no_election_in_window: ['No post-2022 election by Oct. 2025', 'Нет выборов после 2022 года до октября 2025-го'],
  election_during_shock_year: ['Election in 2022', 'Выборы в 2022 году'],
  multiple_elections_in_endpoint_year: ['Several elections in an endpoint year', 'Несколько выборов в одном из сравниваемых годов'],
  missing_vote_share: ['Vote share unavailable', 'Доля голосов недоступна'],
};

function element(tag, className = '', text = '') {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function number(value, digits = 2) {
  if (value == null) return '–';
  return new Intl.NumberFormat(lang, { maximumFractionDigits: digits }).format(value);
}

function signed(value, digits = 2) {
  if (value == null) return '–';
  return (value > 0 ? '+' : value < 0 ? '−' : '') + number(Math.abs(value), digits);
}

function pct(value) {
  return value == null ? '–' : `${number(value)}%`;
}

function pp(value) {
  return value == null ? '–' : `${signed(value)} ${t('pp', 'п. п.')}`;
}

function country(row) {
  const code = iso2[row.iso];
  return code ? new Intl.DisplayNames([lang], { type: 'region' }).of(code) : row.country;
}

function date(value) {
  return value ? new Intl.DateTimeFormat(lang, { dateStyle: 'medium', timeZone: 'UTC' })
    .format(new Date(value + 'T00:00:00Z')) : '–';
}

function table(root, headings, rows) {
  const result = element('table');
  const head = result.createTHead().insertRow();
  headings.forEach((label) => {
    const th = element('th', '', label);
    th.scope = 'col';
    head.append(th);
  });
  const body = result.createTBody();
  rows.forEach((fields) => {
    const row = body.insertRow();
    fields.forEach((value) => { row.insertCell().textContent = value; });
  });
  root.replaceChildren(result);
}

function interactions(figure, readout, hint) {
  const tooltip = figure.querySelector('.chart-tooltip');
  const marks = [];
  let pinned;
  let lastIndex;

  function placeTooltip(mark, value) {
    const frame = figure.getBoundingClientRect();
    const point = mark.getBoundingClientRect();
    if (dismissActiveTooltip !== dismiss) dismissActiveTooltip?.();
    dismissActiveTooltip = dismiss;
    tooltip.textContent = value;
    tooltip.hidden = false;
    const half = Math.min(tooltip.offsetWidth / 2 + 6, frame.width / 2);
    tooltip.style.left = `${Math.max(half, Math.min(frame.width - half, point.left + point.width / 2 - frame.left))}px`;
    tooltip.style.top = `${point.top + point.height / 2 - frame.top}px`;
  }

  function show(item) {
    if (!item) {
      readout.textContent = hint;
      return;
    }
    readout.replaceChildren(element('strong', '', item.title), element('p', '', item.details));
  }

  function clear() {
    tooltip.hidden = true;
    if (dismissActiveTooltip === dismiss) dismissActiveTooltip = undefined;
    show(pinned);
  }

  function dismiss() {
    pinned?.mark.setAttribute('aria-pressed', 'false');
    pinned = undefined;
    clear();
  }

  function reveal(item) {
    lastIndex = item.index;
    placeTooltip(item.mark, item.short);
    show(item);
  }

  function pin(item) {
    pinned?.mark.setAttribute('aria-pressed', 'false');
    pinned = item;
    item.mark.setAttribute('aria-pressed', 'true');
    reveal(item);
  }

  const navigation = figure.querySelector('.point-navigation');
  if (navigation) {
    const steps = [[-1, t('Previous point', 'Предыдущая точка')], [1, t('Next point', 'Следующая точка')]];
    navigation.replaceChildren(...steps.map(([step, label]) => {
      const button = element('button', '', label);
      button.type = 'button';
      button.addEventListener('click', () => {
        const previous = lastIndex ?? (step > 0 ? -1 : 0);
        pin(marks[(previous + step + marks.length) % marks.length]);
      });
      return button;
    }));
  }

  show();
  tooltip.hidden = true;
  return (mark, title, details, short = details) => {
    const index = marks.length;
    const item = { mark, title, details, short, index };
    marks.push(item);
    mark.tabIndex = index === 0 ? 0 : -1;
    mark.type = 'button';
    mark.setAttribute('aria-label', `${title}. ${details}`);
    mark.setAttribute('aria-pressed', 'false');
    mark.addEventListener('pointerenter', (event) => {
      if (event.pointerType !== 'touch') reveal(item);
    });
    mark.addEventListener('pointerleave', () => {
      if (document.activeElement !== mark) clear();
    });
    mark.addEventListener('focus', () => {
      marks.forEach(({ mark: target }) => { target.tabIndex = target === mark ? 0 : -1; });
      reveal(item);
    });
    mark.addEventListener('blur', clear);
    mark.addEventListener('click', () => {
      if (pinned === item) dismiss();
      else pin(item);
    });
    mark.addEventListener('keydown', (event) => {
      let next = index;
      if (['ArrowRight', 'ArrowDown'].includes(event.key)) next = (index + 1) % marks.length;
      else if (['ArrowLeft', 'ArrowUp'].includes(event.key)) next = (index + marks.length - 1) % marks.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = marks.length - 1;
      else return;
      event.preventDefault();
      marks[next].mark.focus();
    });
  };
}

const hint = () => t('Hover, tap or use Tab and the arrow keys to inspect a point.',
  'Наведите курсор, коснитесь точки или используйте Tab и стрелки.');

function scale(domain, value) {
  return 100 * (value - domain[0]) / (domain[1] - domain[0]);
}

function grid(plot, domain, ticks, horizontal = false, showSign = true) {
  for (const value of ticks) {
    const pos = horizontal ? 100 - scale(domain, value) : scale(domain, value);
    const line = element('span', `gridline ${horizontal ? 'horizontal' : 'vertical'}${value === 0 ? ' zero' : ''}`);
    const tick = element('span', `axis-tick ${horizontal ? 'y' : 'x'}`, showSign ? signed(value, 0) : number(value, 0));
    for (const item of [line, tick]) {
      item.style[horizontal ? 'top' : 'left'] = `${pos}%`;
      item.setAttribute('aria-hidden', 'true');
    }
    plot.append(line, tick);
  }
}

function dot(change) {
  return element('button', `mark ${change < 0 ? 'loss' : change === 0 ? 'neutral' : 'gain'}`);
}

function pairDetails(row) {
  return `${date(row.pre_date)} · ${pct(row.pre_vote_pct)} → ${date(row.post_date)} · ${pct(row.post_vote_pct)} (${pp(row.change_pp)})`;
}

function voteChart() {
  dismissActiveTooltip?.();
  const kind = $('#vote-filter input:checked').value;
  const presidential = kind === 'presidential';
  const rows = data.pairs.filter((row) => presidential ? row.type === 'presidential' :
    row.type === 'legislative' && row.kind === kind)
    .sort((a, b) => a.change_pp - b.change_pp || a.country.localeCompare(b.country));
  const figure = $('#vote-figure');
  const plot = $('#vote-plot');
  const bind = interactions(figure, $('#vote-readout'), hint());
  const domain = presidential ? [-25, 60] : [-27, 42];
  const lanes = [];
  plot.replaceChildren();
  grid(plot, domain, presidential ? [-20, 0, 20, 40, 60] : [-20, 0, 20, 40]);
  for (const row of rows) {
    const left = scale(domain, row.change_pp);
    let lane = lanes.findIndex((right) => left - right >= 5.5);
    if (lane < 0) lane = lanes.length;
    lanes[lane] = left;
    const mark = dot(row.change_pp);
    mark.style.left = `${left}%`;
    mark.style.top = `${18 + 18 * lane}px`;
    const title = `${country(row)} · ${t(...crisisNames[row.kind])} ${row.year}`;
    bind(mark, title, pairDetails(row), `${country(row)} · ${pp(row.change_pp)}`);
    plot.append(mark);
  }
  plot.style.height = `${Math.max(75, lanes.length * 18 + 20)}px`;
  const counts = [
    [rows.filter((row) => row.change_pp > 0).length, t('Gained', 'Прирост'), ''],
    [rows.filter((row) => row.change_pp < 0).length, t('Lost', 'Снижение'), 'loss'],
    [rows.filter((row) => row.change_pp === 0).length, t('Unchanged', 'Без изменений'), 'neutral'],
  ];
  $('#vote-stats').replaceChildren(...counts.map(([value, label, tone]) => {
    const block = element('div', `stat ${tone}`);
    block.append(element('strong', '', String(value)), element('span', '', label));
    return block;
  }));
  table($('#vote-table'), [
    t('Country', 'Страна'), t('Crisis', 'Кризис'), t('Before', 'До'), t('After', 'После'), t('Change', 'Сдвиг'),
  ], rows.map((row) => [
    country(row), `${t(...crisisNames[row.kind])} · ${row.year}`,
    `${date(row.pre_date)} · ${pct(row.pre_vote_pct)}`,
    `${date(row.post_date)} · ${pct(row.post_vote_pct)}`, pp(row.change_pp),
  ]));
}

function scatter(plot, points, x, y, xDomain, yDomain, xTicks, yTicks, bind, describe) {
  plot.replaceChildren();
  grid(plot, xDomain, xTicks);
  grid(plot, yDomain, yTicks, true);
  for (const row of points) {
    const mark = dot(y(row));
    mark.style.left = `${scale(xDomain, x(row))}%`;
    mark.style.top = `${100 - scale(yDomain, y(row))}%`;
    bind(mark, ...describe(row));
    plot.append(mark);
  }
}

function incumbentChart() {
  const rows = data.pairs.filter((row) => row.type === 'legislative' && row.kind === 'banking'
    && row.pm_change_pp != null).sort((a, b) => a.pm_change_pp - b.pm_change_pp);
  const bind = interactions($('#incumbent-figure'), $('#incumbent-readout'), hint());
  scatter($('#incumbent-plot'), rows, (row) => row.pm_change_pp, (row) => row.change_pp,
    [-27, 10], [-13, 38], [-25, -15, -5, 0, 10], [-10, 0, 10, 20, 30], bind, (row) => [
      `${country(row)} · ${row.year}`,
      `${t('Head of government’s party', 'Партия главы правительства')} (${row.pm_party}): ${pct(row.pm_pre_pct)} → ${pct(row.pm_post_pct)} (${pp(row.pm_change_pp)}). ${t('Populists', 'Популисты')}: ${pairDetails(row)}.`,
      `${country(row)} · ${pp(row.pm_change_pp)} / ${pp(row.change_pp)}`,
    ]);
  table($('#incumbent-table'), [t('Country', 'Страна'), t('Crisis', 'Кризис'),
    t('Head of government’s party', 'Партия главы правительства'), t('Party vote change', 'Сдвиг у партии'),
    t('Populist vote change', 'Изменение доли голосов')], rows.map((row) => [
    country(row), String(row.year), row.pm_party, pp(row.pm_change_pp), pp(row.change_pp),
  ]));
}

function brazilChart() {
  dismissActiveTooltip?.();
  const issue = $('#brazil-filter input:checked').value;
  const rows = data.brazil.filter((row) => row.issue === issue).sort((a, b) => a.wave - b.wave);
  const peak = Math.max(...rows.map((row) => row.pct_all));
  const bind = interactions($('#brazil-figure'), $('#brazil-readout'),
    t('Hover, tap or focus a wave for its value and sample size.',
      'Наведите курсор, коснитесь столбца или выберите его с клавиатуры.'));
  const guides = element('div', 'bar-guides');
  guides.setAttribute('aria-hidden', 'true');
  grid(guides, [0, 40], [0, 10, 20, 30, 40], true, false);
  $('#brazil-plot').replaceChildren(guides, ...rows.map((row) => {
    const slot = element('div', 'bar-slot');
    const mark = element('button', `bar-button ${row.pct_all === peak ? 'peak' : ''}`);
    mark.style.setProperty('--height', `${row.pct_all / 40 * 100}%`);
    const title = `${t(...issueNames[issue])} · ${row.wave}`;
    const monthFormat = new Intl.DateTimeFormat(lang, { month: 'short', timeZone: 'UTC' });
    const months = String(row.fieldwork_months).split(',').map((month) => monthFormat.format(
      new Date(Date.UTC(row.wave, Number(month) - 1, 1)))).join(' / ');
    bind(mark, title, `${pct(row.pct_all)} · n = ${number(row.n, 0)} · ${months}`, `${row.wave} · ${pct(row.pct_all)}`);
    slot.append(mark, element('span', '', String(row.wave)));
    return slot;
  }));
  table($('#brazil-table'), [t('Wave', 'Волна'), t('Respondents naming issue', 'Доля назвавших тему'),
    t('Sample', 'Выборка')], rows.map((row) => [String(row.wave), pct(row.pct_all), number(row.n, 0)]));
}

function pricesChart() {
  const rows = [...data.prices].sort((a, b) => a.price_change_pp - b.price_change_pp);
  const bind = interactions($('#prices-figure'), $('#prices-readout'), hint());
  scatter($('#prices-plot'), rows.filter((row) => row.status === 'paired'),
    (row) => row.price_change_pp, (row) => row.vote_change_pp, [15, 45], [-5, 20],
    [15, 25, 35, 45], [-5, 0, 5, 10, 15, 20], bind, (row) => [
      country(row),
      `${t('Prices in the survey', 'Цены в опросе')}: ${pct(row.price_2021)} → ${pct(row.price_2022)} (${pp(row.price_change_pp)}). ${t('Populist vote', 'Доля голосов за популистов')}: ${date(row.pre_date)} · ${pct(row.pre_vote_pct)} → ${date(row.post_date)} · ${pct(row.post_vote_pct)} (${pp(row.vote_change_pp)}).`,
      `${country(row)} · ${pp(row.price_change_pp)} / ${pp(row.vote_change_pp)}`,
    ]);
  table($('#prices-table'), [t('Country', 'Страна'), t('Price mentions, change', 'Сдвиг упоминаний цен'),
    t('Before', 'Выборы до'), t('After', 'Выборы после'), t('Populist vote change or reason for exclusion', 'Сдвиг голосов или причина исключения')],
  rows.map((row) => [country(row), pp(row.price_change_pp), date(row.pre_date), date(row.post_date),
    row.status === 'paired' ? pp(row.vote_change_pp) : t(...priceStatus[row.status])]));
}

function render() {
  document.documentElement.lang = lang;
  document.title = t('When does a crisis strengthen populists?', 'Когда кризис усиливает популистов?');
  for (const link of document.querySelectorAll('[data-locale]')) {
    if (link.hreflang === lang) link.setAttribute('aria-current', 'true');
    else link.removeAttribute('aria-current');
  }
  voteChart();
  incumbentChart();
  brazilChart();
  pricesChart();
}

for (const link of document.querySelectorAll('[data-locale]')) {
  link.addEventListener('click', (event) => {
    if (location.protocol === 'file:' || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    lang = link.hreflang;
    const url = new URL(location.href);
    url.searchParams.set('lang', lang);
    history.replaceState(null, '', url);
    render();
  });
}
if (location.protocol === 'file:') {
  document.querySelectorAll('[data-methods]').forEach((link) => { link.href = '../CRISIS_METHODS.md'; });
}
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') dismissActiveTooltip?.();
});
window.addEventListener('popstate', () => { lang = languageFromUrl(); render(); });
$('#vote-filter').addEventListener('change', voteChart);
$('#brazil-filter').addEventListener('change', brazilChart);
render();

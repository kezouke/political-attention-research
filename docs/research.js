'use strict';
const R = window.RESEARCH_DATA;
const lang = document.documentElement.lang === 'ru' ? 'ru' : 'en';
const t = (en, ru) => lang === 'ru' ? ru : en;
const n = (x, digits=2) => new Intl.NumberFormat(lang,{maximumFractionDigits:digits}).format(x);
const signed = x => (x>0?'+':'')+n(x);
const iso2 = {ARG:'AR',BEL:'BE',BGR:'BG',BOL:'BO',BRA:'BR',COL:'CO',DEU:'DE',DNK:'DK',ECU:'EC',ESP:'ES',FIN:'FI',GBR:'GB',GRC:'GR',IND:'IN',IRL:'IE',ISL:'IS',ITA:'IT',JPN:'JP',LVA:'LV',NLD:'NL',NOR:'NO',PHL:'PH',POL:'PL',PRT:'PT',ROU:'RO',TUR:'TR',USA:'US',VEN:'VE'};
const country = r => new Intl.DisplayNames([lang],{type:'region'}).of(iso2[r.iso])+' '+r.onset_year;
const topics = {economy:['Economy','Экономика'],anticorruption:['Anticorruption','Борьба с коррупцией'],environment:['Environmental protection','Охрана окружающей среды']};
function table(target,heads,rows){
  const el=document.createElement('table'),head=document.createElement('thead'),hr=document.createElement('tr');
  heads.forEach(h=>{const th=document.createElement('th');th.scope='col';th.textContent=h;hr.append(th)});head.append(hr);el.append(head);
  const body=document.createElement('tbody');rows.forEach(row=>{const tr=document.createElement('tr');row.forEach((v,i)=>{const td=document.createElement(i?'td':'th');if(!i)td.scope='row';td.textContent=v;tr.append(td)});body.append(tr)});el.append(body);document.getElementById(target).replaceChildren(el);
}
function renderTopic(){
  const topic=document.getElementById('topic-select').value;
  for(const l of ['ru','en']){
    const image=document.getElementById('decomposition-image-'+l);image.src='figures/decomposition-'+topic+'-'+l+'.svg';image.alt=topics[topic][l==='ru'?1:0];
    document.getElementById('decomposition-mobile-'+l).srcset='figures/decomposition-'+topic+'-mobile-'+l+'.svg';
    document.getElementById('decomposition-caption-'+l).textContent=topics[topic][l==='ru'?1:0]+'. '+(l==='ru'?'16 эпизодов, охват программ не менее 75% голосов на обоих концах. Точка показывает сумму компонентов. Изменение состава записей включает пропуски и изменения партийных идентификаторов.':'Sixteen episodes, with programme coverage of at least 75% of votes at both endpoints. Diamonds show the sum of the components. Roster changes include missing records and changed party identifiers.');
  }
  const rows=R.programmes.filter(r=>r.topic===topic).sort((a,b)=>a.change_pp-b.change_pp);
  table('decomposition-table',t(['Country / crisis','Before, %','After, %','Programmes, pp','Votes, pp','Roster, pp','Coverage, %'],['Страна / кризис','До, %','После, %','Программы, п. п.','Голоса, п. п.','Состав, п. п.','Охват, %']),rows.map(r=>[country(r),n(r.pre_share),n(r.post_share),signed(r.within_pp),signed(r.reweight_pp),signed(r.roster_pp),n(r.pre_coverage,1)+' → '+n(r.post_coverage,1)]));
}
for(const o of document.getElementById('topic-select').options)o.textContent=topics[o.value][lang==='ru'?1:0];
document.getElementById('topic-select').addEventListener('change',renderTopic);renderTopic();
table('horizon-table',t(['Country / crisis','First election','Change, pp','Second election','Change, pp'],['Страна / кризис','Первые выборы','Сдвиг, п. п.','Вторые выборы','Сдвиг, п. п.']),R.horizon.map(r=>[country(r),r.date_first,signed(r.change_pp_first),r.date_second,signed(r.change_pp_second)]));
document.title=t('After a crisis: new programmes or new winners?','После кризиса: новые программы или новые победители?');
for(const a of document.querySelectorAll('[data-locale]'))a.href='?lang='+a.hreflang+location.hash;

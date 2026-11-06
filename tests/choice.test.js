const fs = require('fs');
const vm = require('vm');
const path = require('path');
const source = fs.readFileSync(path.resolve(__dirname, '../docs/choice.js'), 'utf8');
for (const lang of ['ru', 'en']) {
  const links = [{ hreflang: 'en' }, { hreflang: 'ru' }];
  const events = {};
  const context = {
    document: { documentElement: { lang }, querySelectorAll: () => links },
    location: { hash: '#countries' },
    window: { addEventListener: (name, fn) => { events[name] = fn; } }
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  if (!context.document.title.includes(lang === 'ru' ? 'недовольство' : 'discontent')) throw Error('Wrong page title');
  if (links[0].href !== '?lang=en#countries' || links[1].href !== '?lang=ru#countries') throw Error('Language switch loses section');
  context.location.hash = '#before';
  events.hashchange();
  if (links[0].href !== '?lang=en#before') throw Error('Changed section lost');
}
console.log('Both languages preserve the selected essay section');

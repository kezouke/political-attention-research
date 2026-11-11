'use strict';
const russian = document.documentElement.lang === 'ru';
document.title = russian ? 'За кого голосуют, когда экономике плохо' : 'Who do people vote for when the economy is doing badly?';
function preserveSection() {
  for (const link of document.querySelectorAll('[data-locale]')) {
    link.href = '?lang=' + link.hreflang + location.hash;
  }
}
preserveSection();
window.addEventListener('hashchange', preserveSection);

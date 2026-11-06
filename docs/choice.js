'use strict';
const russian = document.documentElement.lang === 'ru';
document.title = russian ? 'После кризиса: кому достаётся недовольство?' : 'After a crisis, who receives discontent?';
function preserveSection() {
  for (const link of document.querySelectorAll('[data-locale]')) {
    link.href = '?lang=' + link.hreflang + location.hash;
  }
}
preserveSection();
window.addEventListener('hashchange', preserveSection);

/* Runs before the stylesheet so a saved theme is applied before first paint. */
(() => {
  'use strict';
  const key = 'mateopctech-theme';
  const root = document.documentElement;
  let saved;
  try { saved = localStorage.getItem(key); } catch { /* Storage may be blocked. */ }
  const preference = window.matchMedia('(prefers-color-scheme: light)');
  let explicit = saved === 'light' || saved === 'dark';
  let theme = explicit ? saved : (preference.matches ? 'light' : 'dark');
  root.dataset.theme = theme;

  document.addEventListener('DOMContentLoaded', () => {
    const button = document.querySelector('[data-theme-toggle]');
    if (!button) return;
    function render() {
      root.dataset.theme = theme;
      const next = theme === 'dark' ? 'light' : 'dark';
      button.setAttribute('aria-label', `Switch to ${next} mode`);
      button.setAttribute('title', `Switch to ${next} mode`);
      button.querySelector('[data-theme-label]').textContent = `${next[0].toUpperCase()}${next.slice(1)} mode`;
    }
    button.addEventListener('click', () => {
      theme = theme === 'dark' ? 'light' : 'dark';
      explicit = true;
      try { localStorage.setItem(key, theme); } catch { /* Keep working for this page. */ }
      render();
    });
    preference.addEventListener('change', () => {
      if (!explicit) {
        theme = preference.matches ? 'light' : 'dark';
        render();
      }
    });
    render();
    button.hidden = false;
  });
})();

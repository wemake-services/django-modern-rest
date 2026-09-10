// Shibuya does not preserve the left sidebar's scroll position between pages.
// Save and restore it so users do not lose their place in the navigation.
// https://github.com/wemake-services/django-modern-rest/issues/1396
(() => {
  const key = 'dmr:sidebar-scroll';

  document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.querySelector('#lside .sy-scrollbar');
    if (!sidebar) return;

    try {
      const saved = sessionStorage.getItem(key);
      if (saved !== null) {
        const position = Number(saved);
        if (Number.isFinite(position) && position >= 0) {
          sidebar.scrollTop = position;
        }
      }
    } catch {
      // Browser settings may prevent access to storage.
    }

    window.addEventListener('pagehide', () => {
      try {
        sessionStorage.setItem(key, String(sidebar.scrollTop));
      } catch {
        // Navigation still works when storage is unavailable.
      }
    });
  });
})();

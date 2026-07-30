(function() {
  const charts = new Map();

  function renderCharts() {
    if (typeof Chart === 'undefined') return;

    const theme = document.documentElement.classList.contains('dark')
      ? 'dark'
      : 'light';

    document.querySelectorAll('[data-chartjs-config]').forEach((script) => {
      const chartId = script.dataset.chartjsTarget;
      const canvas = document.getElementById(chartId);
      if (!canvas) return;

      const config = JSON.parse(script.textContent)[theme];

      charts.get(chartId)?.destroy();
      charts.set(chartId, new Chart(canvas.getContext('2d'), config));
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderCharts);
  } else {
    renderCharts();
  }

  new MutationObserver(renderCharts).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  });
})();

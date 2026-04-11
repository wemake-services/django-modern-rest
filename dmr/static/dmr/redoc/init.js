(() => {
  const app = document.getElementById('redoc-app');
  const schemaNode = document.getElementById('redoc-schema');
  const init = window.Redoc?.init;

  if (!app || !schemaNode || !init) return;

  try {
    const schema = JSON.parse(schemaNode.textContent ?? '');
    if (!schema) return;

    init(schema, {}, app);
  } catch (e) {
    console.error('Invalid ReDoc schema:', e);
  }
})();

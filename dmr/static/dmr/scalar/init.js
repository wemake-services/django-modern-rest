(() => {
  const app = document.getElementById('scalar-app');
  const schemaNode = document.getElementById('scalar-schema');
  const createApiReference = window.Scalar?.createApiReference;

  if (!app || !schemaNode || !createApiReference) return;

  try {
    const schema = JSON.parse(schemaNode.textContent ?? '');
    if (!schema) return;

    createApiReference('#scalar-app', {
      sources: [{ content: schema }],
    });
  } catch (e) {
    console.error('Invalid Scalar schema:', e);
  }
})();

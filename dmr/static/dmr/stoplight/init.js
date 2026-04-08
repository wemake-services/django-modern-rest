(() => {
  const app = document.getElementById('stoplight-app');
  const schemaNode = document.getElementById('stoplight-schema');

  if (!app || !schemaNode) return;

  try {
    const schema = JSON.parse(schemaNode.textContent ?? '');
    if (!schema) return;

    app.apiDescriptionDocument = JSON.stringify(schema);
  } catch (e) {
    console.error('Invalid Stoplight schema:', e);
  }
})();

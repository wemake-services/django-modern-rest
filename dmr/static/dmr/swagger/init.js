(() => {
  const app = document.getElementById('swagger-app');
  const schemaNode = document.getElementById('swagger-schema');
  const SwaggerUIBundle = window.SwaggerUIBundle;
  const SwaggerUIStandalonePreset = window.SwaggerUIStandalonePreset;

  if (!app || !schemaNode || !SwaggerUIBundle || !SwaggerUIStandalonePreset) return;

  try {
    const schema = JSON.parse(schemaNode.textContent ?? '');
    if (!schema) return;

    SwaggerUIBundle({
      spec: schema,
      dom_id: '#swagger-app',
      deepLinking: true,
      presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIStandalonePreset,
      ],
      plugins: [
        SwaggerUIBundle.plugins.DownloadUrl,
      ],
      layout: 'StandaloneLayout',
      requestInterceptor: (req) => {
        const csrfToken = app.dataset.csrfToken;
        if (csrfToken) {
          req.headers['X-CSRFToken'] = csrfToken;
        }
        return req;
      },
    });
  } catch (e) {
    console.error('Invalid Swagger schema:', e);
  }
})();

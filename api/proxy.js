module.exports = async function handler(req, res) {
  const backendUrl = process.env.BACKEND_URL;
  if (!backendUrl) {
    res.status(503).json({ error: 'BACKEND_URL is not configured' });
    return;
  }

  const path = Array.isArray(req.query.path) ? req.query.path.join('/') : req.query.path || '';
  const incomingUrl = new URL(req.url || '/', `https://${req.headers.host || 'localhost'}`);
  incomingUrl.searchParams.delete('path');

  const targetUrl = new URL(`/api/${path}`, backendUrl);
  targetUrl.search = incomingUrl.search;

  const headers = new Headers();
  headers.set('accept', req.headers.accept || 'application/json');
  headers.set('content-type', req.headers['content-type'] || 'application/json');

  if (req.headers.authorization) {
    headers.set('authorization', req.headers.authorization);
  }

  const requestBody = ['GET', 'HEAD'].includes(req.method || '')
    ? undefined
    : typeof req.body === 'string' || Buffer.isBuffer(req.body)
      ? req.body
      : JSON.stringify(req.body || {});

  try {
    const upstream = await fetch(targetUrl, {
      method: req.method,
      headers,
      body: requestBody
    });

    const contentType = upstream.headers.get('content-type') || 'application/json; charset=utf-8';
    res.setHeader('content-type', contentType);
    res.setHeader('cache-control', 'no-store');
    res.status(upstream.status).send(await upstream.text());
  } catch (error) {
    res.status(502).json({
      error: 'Backend tunnel unreachable',
      detail: error instanceof Error ? error.message : String(error)
    });
  }
};

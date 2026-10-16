// brief-sounds (tools/sounds.py, 2026-10-16): serves the daily brief's sounds from the Worker's
// static assets, and answers byte-range requests. Static assets alone answer every request with
// 200 and the whole file, and iPhone Safari wants 206 Partial Content before it will play audio
// (the Echo uses ranges to resume). Ranges are cut from the stream, so nothing is buffered.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const res = await env.ASSETS.fetch(request);
    const headers = new Headers(res.headers);
    headers.set('X-Robots-Tag', 'noindex');
    if (/^\/(m|a)\//.test(url.pathname) && res.status === 200) {
      headers.set('Cache-Control', 'public, max-age=31536000, immutable');
    }
    if (res.status !== 200 || !/^audio\//.test(headers.get('Content-Type') || '')) {
      return new Response(res.body, { status: res.status, headers });
    }
    headers.set('Accept-Ranges', 'bytes');
    const m = /^bytes=(\d*)-(\d*)$/.exec((request.headers.get('Range') || '').trim());
    if (!m || (m[1] === '' && m[2] === '')) {
      return new Response(request.method === 'HEAD' ? null : res.body, { status: 200, headers });
    }
    // A cached asset can arrive without Content-Length; then read it (the files are a few MB).
    let size = Number(headers.get('Content-Length'));
    let whole = null;
    if (!size) {
      whole = await res.arrayBuffer();
      size = whole.byteLength;
    }
    let start, end;
    if (m[1] === '') { start = Math.max(0, size - Number(m[2])); end = size - 1; }   // the last N bytes
    else { start = Number(m[1]); end = m[2] === '' ? size - 1 : Math.min(Number(m[2]), size - 1); }
    if (start >= size || start > end) {
      headers.set('Content-Range', `bytes */${size}`);
      headers.delete('Content-Length');
      return new Response(null, { status: 416, headers });
    }
    headers.set('Content-Range', `bytes ${start}-${end}/${size}`);
    headers.set('Content-Length', String(end - start + 1));
    if (request.method === 'HEAD') return new Response(null, { status: 206, headers });
    if (whole) return new Response(new Uint8Array(whole, start, end - start + 1), { status: 206, headers });
    let pos = 0;
    const { readable, writable } = new TransformStream({
      transform(chunk, ctrl) {
        const next = pos + chunk.byteLength;
        if (next > start && pos <= end) {
          ctrl.enqueue(chunk.subarray(Math.max(0, start - pos), Math.min(chunk.byteLength, end - pos + 1)));
        }
        pos = next;
        if (pos > end) ctrl.terminate();
      },
    });
    res.body.pipeTo(writable).catch(() => {});
    return new Response(readable, { status: 206, headers });
  },
};

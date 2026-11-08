// Demo mode runs entirely in the browser with simulated tanks (no backend needed): open index.html?mock=1
// Normal mode talks to the FastAPI backend that serves this page.
const params = new URLSearchParams(location.search);

export const CONFIG = {
  mock: params.get('mock') === '1',
  api: '/api/v1',
};

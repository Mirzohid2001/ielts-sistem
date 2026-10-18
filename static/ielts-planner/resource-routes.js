// Routes are injected by Django as #plannerResourceRoutes (json_script).
export const TON_ROUTES = {
  readingVideo: '/videos/?search=Reading',
  writingVideo: '/videos/?search=Writing',
  listeningVideo: '/videos/?search=Listening',
  grammarVideo: '/mashqlar/grammar/',
  readingExercise: '/mashqlar/reading/',
  writingExercise: '/mashqlar/writing/',
  cdiReading: '/tests/collection/reading/',
  cdiListening: '/tests/collection/listening/',
  cdiWriting: '/tests/collection/writing/'
};

function loadServerRoutes() {
  const node = document.getElementById('plannerResourceRoutes');
  if (!node) return {};
  try {
    const parsed = JSON.parse(node.textContent || '{}');
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch (error) {
    return {};
  }
}

export function applyResourceRoutes(resources, origin = location.origin) {
  const routes = Object.assign({}, TON_ROUTES, loadServerRoutes());
  for (const [key, value] of Object.entries(routes)) {
    if (!value || !resources[key]) continue;
    const url = new URL(value, origin);
    if (url.protocol !== 'https:' && url.origin !== origin) {
      throw new Error('Resource URL must use HTTPS');
    }
    resources[key].url = url.href;
  }
}

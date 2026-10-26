const bag = (() => {
  try {
    return JSON.parse(document.getElementById('vocabLabI18n')?.textContent || '{}');
  } catch {
    return {};
  }
})();

export function t(key, vars = {}) {
  let s = bag[key];
  if (s == null || s === '') return key;
  return String(s).replace(/\{(\w+)\}/g, (_, name) => (vars[name] != null ? String(vars[name]) : ''));
}

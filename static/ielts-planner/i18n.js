const bag = (() => {
  try {
    return JSON.parse(document.getElementById('plannerI18n')?.textContent || '{}');
  } catch {
    return {};
  }
})();

const UZ_DAYS = ['Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba', 'Yakshanba'];
const UZ_SHORT = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya'];
const UZ_MONTHS = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr'];

export const DAY_NAMES = Array.isArray(bag.dayNames) && bag.dayNames.length === 7 ? bag.dayNames : UZ_DAYS;
export const DAY_SHORT = Array.isArray(bag.dayShort) && bag.dayShort.length === 7 ? bag.dayShort : UZ_SHORT;
export const MONTHS = Array.isArray(bag.months) && bag.months.length === 12 ? bag.months : UZ_MONTHS;

export function t(key, vars = {}) {
  let s = bag[key];
  if (s == null || s === '') return key;
  return String(s).replace(/\{(\w+)\}/g, (_, name) => (vars[name] != null ? String(vars[name]) : ''));
}

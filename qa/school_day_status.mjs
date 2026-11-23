// Pure status checks shared by the artificial browser journey and its tests.
// Reading a status must never create or retry work.
export function hasActivePreparation(day) {
  return Boolean(day.active_job) || ['processing', 'queued', 'running'].includes(day.preparation?.status);
}

export function pagePreparationSettled(day) {
  return Array.isArray(day.pages) && day.pages.length === 2 &&
    day.pages.every(page => ['review', 'confirmed'].includes(page.status)) &&
    !hasActivePreparation(day);
}

export function preparationFailureCode(day, fallback) {
  return day.preparation?.phase === 'package'
    ? 'automatic_package_failed_no_automatic_retry'
    : fallback + '_failed_no_automatic_retry';
}

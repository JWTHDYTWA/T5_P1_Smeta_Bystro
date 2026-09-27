/**
 * Утилиты, общие для всех страниц:
 *  - сохранение черновика формы в localStorage (раздел 1.1 "Работа на слабой сети":
 *    введённые данные не теряются при обрыве связи);
 *  - единый рендер баннера ошибки/предупреждения.
 */

function saveDraft(key, value) {
  try {
    localStorage.setItem("draft:" + key, JSON.stringify(value));
  } catch (e) {
    // localStorage недоступен (приватный режим и т.п.) — не критично для MVP
    console.warn("Не удалось сохранить черновик", e);
  }
}

function loadDraft(key) {
  try {
    const raw = localStorage.getItem("draft:" + key);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function clearDraft(key) {
  try {
    localStorage.removeItem("draft:" + key);
  } catch (e) {}
}

function showError(container, err, kind) {
  kind = kind || "banner-error";
  container.innerHTML = `<div class="${kind}">${escapeHtml(err.message || "Произошла ошибка")}</div>` + container.innerHTML;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatMoney(n) {
  return Number(n).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

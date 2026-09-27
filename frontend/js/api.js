/**
 * Тонкая обёртка над fetch(): всегда шлёт cookie сессии, приводит ошибки
 * API к единому виду {code, message} (см. раздел 3.1 ТЗ), и по 401 сама
 * перекидывает на экран входа.
 */
const API_BASE = "";

async function apiRequest(method, path, body) {
  let response;
  try {
    response = await fetch(API_BASE + path, {
      method,
      credentials: "include",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (networkErr) {
    // Сервис недоступен (ПК выключен / нет сети) — раздел 3.1 "Обработка сбоев"
    throw { code: "NETWORK_ERROR", message: "Нет соединения с сервером. Проверьте подключение и повторите попытку." };
  }

  if (response.status === 401) {
    window.location.href = "/login.html";
    throw { code: "UNAUTHORIZED", message: "Войдите заново по номеру телефона" };
  }

  if (!response.ok) {
    let payload;
    try {
      payload = await response.json();
    } catch {
      throw { code: "UNKNOWN", message: "Произошла ошибка, попробуйте ещё раз" };
    }
    throw payload.error || { code: "UNKNOWN", message: "Произошла ошибка, попробуйте ещё раз" };
  }

  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response;
}

const api = {
  get: (path) => apiRequest("GET", path),
  post: (path, body) => apiRequest("POST", path, body),
};

/** @typedef {{ message: string, data?: unknown }} ApiEnvelope */

import { clearChatStorage } from "./context/ChatContext.jsx";

const TOKEN_KEY = "semantic_token";

function handleUnauthorized(status) {
  if (status !== 401) return;
  const path = window.location.pathname;
  if (path === "/login" || path === "/register") return;
  clearToken();
  clearChatStorage();
  window.location.assign("/login");
}

export function getApiBase() {
  const base = import.meta.env.VITE_API_BASE_URL;
  if (!base) {
    throw new Error("Set VITE_API_BASE_URL in frontend/.env (see .env.example)");
  }
  return base.replace(/\/$/, "");
}

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

/**
 * @param {string} method
 * @param {string} path
 * @param {{ body?: object, token?: string | null }} [opts]
 */
export async function jsonRequest(method, path, opts = {}) {
  const url = `${getApiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = {};
  if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (opts.token) {
    headers["Authorization"] = `Bearer ${opts.token}`;
  }
  const response = await fetch(url, {
    method,
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  /** @type {ApiEnvelope} */
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("Invalid response from server.");
  }
  if (!response.ok) {
    handleUnauthorized(response.status);
    const msg =
      typeof data.message === "string" ? data.message : `Request failed (${response.status}).`;
    throw new Error(msg);
  }
  return data;
}

/**
 * @param {string} path
 * @param {FormData} formData
 * @param {string} token
 */
export async function formRequest(path, formData, token) {
  const url = `${getApiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
  /** @type {ApiEnvelope} */
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("Invalid response from server.");
  }
  if (!response.ok) {
    handleUnauthorized(response.status);
    const msg =
      typeof data.message === "string" ? data.message : `Request failed (${response.status}).`;
    throw new Error(msg);
  }
  return data;
}

/**
 * @param {string} path
 * @param {string} token
 */
export async function deleteRequest(path, token) {
  const url = `${getApiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  /** @type {ApiEnvelope} */
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("Invalid response from server.");
  }
  if (!response.ok) {
    handleUnauthorized(response.status);
    const msg =
      typeof data.message === "string" ? data.message : `Request failed (${response.status}).`;
    throw new Error(msg);
  }
  return data;
}

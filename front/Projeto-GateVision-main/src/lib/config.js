import { createClient } from "@supabase/supabase-js";

export const SUPABASE_URL = "https://blulbaobttmwewxvttql.supabase.co";
export const SUPABASE_KEY = "sb_publishable_RAYD5x0h3bSgkdToX39u8Q_JFYQkZyi";
export const SESSION_KEY = "gv_session";
export const BACKEND_STORAGE_KEY = "gv_backend_url";
export const ESTAB_ID = 1;

export const db = createClient(SUPABASE_URL, SUPABASE_KEY);

export function resolveBackendUrl() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("backend");
  if (fromQuery) {
    const clean = fromQuery.replace(/\/$/, "");
    localStorage.setItem(BACKEND_STORAGE_KEY, clean);
    return clean;
  }

  const fromStorage = localStorage.getItem(BACKEND_STORAGE_KEY);
  if (fromStorage) return fromStorage.replace(/\/$/, "");
  if (window.GATEVISION_BACKEND_URL) return String(window.GATEVISION_BACKEND_URL).replace(/\/$/, "");
  return "http://localhost:8000";
}

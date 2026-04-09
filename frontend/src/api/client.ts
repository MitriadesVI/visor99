const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function fetchJson<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
  signal?: AbortSignal,
): Promise<T> {
  const base = API_BASE_URL || window.location.origin;
  const url = new URL(path, base);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === "" || value === "Todos") {
        return;
      }
      url.searchParams.set(key, String(value));
    });
  }

  const response = await fetch(url.toString(), {
    signal,
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

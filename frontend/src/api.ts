function messages(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(messages).join(" ");
  if (value && typeof value === "object")
    return Object.values(value).map(messages).join(" ");
  return "No se pudo completar la operación.";
}
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const token =
    document.cookie
      .split("; ")
      .find((x) => x.startsWith("csrftoken="))
      ?.split("=")[1] || "";
  const form = data instanceof FormData;
  const response = await fetch(`/api/${path}`, {
    method,
    credentials: "same-origin",
    headers: {
      ...(form ? {} : { "Content-Type": "application/json" }),
      "X-CSRFToken": decodeURIComponent(token),
    },
    body: data === undefined ? undefined : form ? data : JSON.stringify(data),
  });
  const result = await response
    .json()
    .catch(() => ({ detail: "El servidor no respondió correctamente." }));
  if (!response.ok)
    throw new ApiError(
      response.status === 403
        ? "La sesión venció o no tenés permiso para esta acción. Ingresá nuevamente."
        : messages(result),
      response.status,
    );
  return result as T;
}

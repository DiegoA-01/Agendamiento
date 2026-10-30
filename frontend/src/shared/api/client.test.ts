import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, cursorFrom, readCookie } from "./client";

const fetchMock = vi.fn();

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status });
}

function lastCall() {
  const [path, init] = fetchMock.mock.calls.at(-1) as [string, RequestInit];
  return { path, init, headers: init.headers as Record<string, string> };
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("document", { cookie: "csrftoken=abc123; theme=dark" });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("readCookie", () => {
  it("lee y decodifica una cookie", () => {
    vi.stubGlobal("document", { cookie: "a=1; token=hola%20mundo" });
    expect(readCookie("token")).toBe("hola mundo");
    expect(readCookie("falta")).toBeNull();
  });

  it("no falla sin document", () => {
    vi.unstubAllGlobals();
    expect(readCookie("csrftoken")).toBeNull();
  });
});

describe("api", () => {
  it("las lecturas no llevan token CSRF ni lo piden", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }));
    await api("/api/v1/me/");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(lastCall().headers["X-CSRFToken"]).toBeUndefined();
    expect(lastCall().init.credentials).toBe("same-origin");
  });

  it("las escrituras llevan el token de la cookie y el cuerpo en JSON", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 1 }, 201));
    await api("/api/v1/plans/", { method: "post", body: { name: "Pro" } });
    const { headers, init } = lastCall();
    expect(init.method).toBe("POST");
    expect(headers["X-CSRFToken"]).toBe("abc123");
    expect(headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe('{"name":"Pro"}');
  });

  it("si aún no hay cookie, pide el token antes de escribir", async () => {
    const doc = { cookie: "" };
    vi.stubGlobal("document", doc);
    fetchMock.mockImplementation(async (path: string) => {
      if (path === "/api/v1/auth/csrf/") {
        doc.cookie = "csrftoken=nuevo";
        return new Response(null, { status: 204 });
      }
      return jsonResponse({});
    });
    await api("/api/v1/auth/login/", { method: "POST", body: {} });
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual([
      "/api/v1/auth/csrf/",
      "/api/v1/auth/login/",
    ]);
    expect(lastCall().headers["X-CSRFToken"]).toBe("nuevo");
  });

  it("relee el token en cada petición: Django lo rota al iniciar sesión", async () => {
    const doc = { cookie: "csrftoken=antes" };
    vi.stubGlobal("document", doc);
    fetchMock.mockResolvedValue(jsonResponse({}));
    await api("/api/v1/auth/login/", { method: "POST", body: {} });
    expect(lastCall().headers["X-CSRFToken"]).toBe("antes");
    doc.cookie = "csrftoken=despues";
    await api("/api/v1/auth/logout/", { method: "POST" });
    expect(lastCall().headers["X-CSRFToken"]).toBe("despues");
  });

  it("una respuesta 204 devuelve undefined", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(api("/api/v1/auth/logout/", { method: "POST" })).resolves.toBeUndefined();
  });

  it("convierte los errores de la API en ApiError con código y campos", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        { code: "validation_error", detail: "Datos inválidos.", fields: { slug: ["Reservado"] } },
        400,
      ),
    );
    const error = (await api("/api/v1/tenants/", { method: "POST", body: {} }).catch(
      (e: unknown) => e,
    )) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 400,
      code: "validation_error",
      fields: { slug: ["Reservado"] },
    });
    expect(error.message).toBe("Datos inválidos.");
  });

  it("un error sin JSON se vuelve código 'unknown'", async () => {
    fetchMock.mockResolvedValue(new Response("<html>502</html>", { status: 502 }));
    const error = await api("/api/v1/me/").catch((e) => e);
    expect(error).toMatchObject({ status: 502, code: "unknown", fields: {} });
  });
});

describe("cursorFrom", () => {
  it("extrae el cursor de la URL de la página siguiente", () => {
    expect(cursorFrom("http://admin.localhost:8080/api/v1/tenants/?cursor=cD0yMDI2&q=aura")).toBe(
      "cD0yMDI2",
    );
    expect(cursorFrom("/api/v1/tenants/?cursor=xyz")).toBe("xyz");
  });

  it("sin página siguiente no hay cursor", () => {
    expect(cursorFrom(null)).toBeUndefined();
    expect(cursorFrom("http://x/api/v1/tenants/")).toBeUndefined();
  });
});

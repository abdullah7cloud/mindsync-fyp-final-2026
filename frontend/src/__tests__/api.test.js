import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "../api";

function mockFetch(status, body) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "x",
    json: async () => body,
  });
}
afterEach(() => vi.restoreAllMocks());

describe("api error handling", () => {
  it("turns a FastAPI validation error into plain English with per-field messages", async () => {
    mockFetch(422, { detail: [{ loc: ["body", "password"], msg: "String should have at least 8 characters" }] });
    const err = await api.register("a@b.com", "short", "Abi").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.fields.password).toMatch(/at least 8 characters/i);
  });
  it("shows the server's message for plain errors (e.g. duplicate email)", async () => {
    mockFetch(409, { detail: "An account with this email already exists." });
    await expect(api.register("a@b.com", "Passw0rdx", "Abi")).rejects.toThrow(/already exists/);
  });
  it("explains when the backend cannot be reached", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("fail"));
    await expect(api.plans("t")).rejects.toThrow(/We cannot reach MindSync right now/);
  });
  it("returns null for 204 No Content and sends the bearer token", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 204 });
    expect(await api.deleteTask("tok", "id1")).toBeNull();
    const [, init] = globalThis.fetch.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer tok");
    expect(init.method).toBe("DELETE");
  });
  it("sends the delete-account password in the body", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 204 });
    await api.deleteAccount("tok", "secret-pass-1");
    expect(JSON.parse(globalThis.fetch.mock.calls[0][1].body)).toEqual({ password: "secret-pass-1" });
  });
});

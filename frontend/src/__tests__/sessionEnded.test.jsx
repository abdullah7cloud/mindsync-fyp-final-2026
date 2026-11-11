import { afterEach, describe, expect, it, vi } from "vitest";
import { api, onSessionEnded } from "../api";

function fakeFetch(status, detail) {
  return vi.fn().mockResolvedValue({ ok: false, status, statusText: "x", json: async () => ({ detail }), headers: { get: () => "" } });
}

describe("an expired login", () => {
  afterEach(() => { onSessionEnded(null); vi.unstubAllGlobals(); });

  it("is explained in plain words and signs the student out instead of showing 'Invalid or expired token'", async () => {
    vi.stubGlobal("fetch", fakeFetch(401, "Invalid or expired token"));
    const handler = vi.fn();
    onSessionEnded(handler);
    await expect(api.plans("old-token")).rejects.toMatchObject({ status: 401, message: expect.stringContaining("log in again") });
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("does the same for uploads and picture downloads", async () => {
    vi.stubGlobal("fetch", fakeFetch(401, "Invalid or expired token"));
    const handler = vi.fn();
    onSessionEnded(handler);
    await expect(api.uploadMyPicture("t", new Blob(["x"]))).rejects.toMatchObject({ status: 401 });
    await expect(api.myPicture("t")).rejects.toMatchObject({ status: 401 });
    expect(handler).toHaveBeenCalledTimes(2);
  });

  it("a wrong password at login (no token sent) is NOT treated as an ended session", async () => {
    vi.stubGlobal("fetch", fakeFetch(401, "Invalid email or password"));
    const handler = vi.fn();
    onSessionEnded(handler);
    await expect(api.login("a@b.com", "x")).rejects.toMatchObject({ message: "Invalid email or password" });
    expect(handler).not.toHaveBeenCalled();
  });

  it("other errors with a token keep their own message", async () => {
    vi.stubGlobal("fetch", fakeFetch(403, "That password is not right."));
    const handler = vi.fn();
    onSessionEnded(handler);
    await expect(api.changePassword("t", "a", "b")).rejects.toMatchObject({ status: 403 });
    expect(handler).not.toHaveBeenCalled();
  });
});

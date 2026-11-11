import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "../api";
import ProfilePage from "../pages/ProfilePage";
import SettingsPage from "../pages/SettingsPage";
import AccountModal from "../components/AccountModal";
import { applyTheme, getTheme, setTheme } from "../theme";

vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ token: "tok", user: { email: "a@b.com", display_name: "Abi" }, refreshUser: async () => {}, logout: () => {} }) }));
beforeEach(() => { localStorage.clear(); delete document.documentElement.dataset.theme; if (!window.URL.createObjectURL) window.URL.createObjectURL = () => "blob:x"; if (!window.URL.revokeObjectURL) window.URL.revokeObjectURL = () => {}; });
afterEach(() => vi.restoreAllMocks());

const at = (path, el) => render(<MemoryRouter initialEntries={[path]}><Routes><Route path={path} element={el} /></Routes></MemoryRouter>);
const prof = (o = {}) => ({ display_name: "Abi Khan", email: "abi@example.com", member_since: "2026-10-01T00:00:00Z", has_picture: false, picture_version: 0, pending_email: null, ...o });
const sets = (o = {}) => ({ remind_enabled: false, remind_percent: 30, timezone: "UTC", delivery: "demo", percent_choices: [30, 35], ...o });

describe("theme", () => {
  it("remembers light, dark and system", () => {
    expect(getTheme()).toBe("system");
    setTheme("dark");
    expect(getTheme()).toBe("dark"); expect(document.documentElement.dataset.theme).toBe("dark"); expect(localStorage.getItem("mindsync_theme")).toBe("dark");
    setTheme("light");
    expect(document.documentElement.dataset.theme).toBe("light");
    setTheme("system");
    expect(getTheme()).toBe("system"); expect(document.documentElement.dataset.theme).toBeUndefined(); expect(localStorage.getItem("mindsync_theme")).toBeNull();
  });
  it("ignores a strange stored value", () => {
    localStorage.setItem("mindsync_theme", "<script>");
    expect(getTheme()).toBe("system");
    applyTheme("nonsense"); expect(document.documentElement.dataset.theme).toBeUndefined();
  });
});

describe("My Profile", () => {
  it("shows the account and saves a new name with a clear confirmation", async () => {
    vi.spyOn(api, "myProfile").mockResolvedValue(prof());
    const save = vi.spyOn(api, "saveMyName").mockResolvedValue(prof({ display_name: "Abi K" }));
    at("/profile", <ProfilePage />);
    expect(await screen.findByText("abi@example.com")).toBeInTheDocument();
    const btn = screen.getByRole("button", { name: "Save name" });
    expect(btn).toBeDisabled();
    const input = screen.getByLabelText("Full name");
    await userEvent.clear(input); await userEvent.type(input, "Abi K");
    await userEvent.click(btn);
    await waitFor(() => expect(save).toHaveBeenCalledWith("tok", "Abi K"));
    expect(await screen.findByText("Your name was saved.")).toBeInTheDocument();
  });
  it("changes e-mail in two steps: password then code", async () => {
    const p = vi.spyOn(api, "myProfile").mockResolvedValueOnce(prof()).mockResolvedValue(prof({ pending_email: { email: "new@example.com", expires_at: "x" } }));
    const start = vi.spyOn(api, "startEmailChange").mockResolvedValue({ message: "If this address can be used, we sent a 6-digit code to it.", delivery: "demo" });
    const confirm = vi.spyOn(api, "confirmEmailChange").mockResolvedValue({ message: "ok", profile: prof({ email: "new@example.com" }) });
    at("/profile", <ProfilePage />);
    await userEvent.click(await screen.findByRole("button", { name: "Change e-mail" }));
    await userEvent.type(screen.getByLabelText("New e-mail address"), "new@example.com");
    await userEvent.type(screen.getByLabelText(/Your password/), "secret-pass-1");
    await userEvent.click(screen.getByRole("button", { name: "Send me a code" }));
    await waitFor(() => expect(start).toHaveBeenCalledWith("tok", "new@example.com", "secret-pass-1"));
    expect(await screen.findByText(/saved as a file in the backend\/outbox folder/)).toBeInTheDocument();
    const confirmBtn = screen.getByRole("button", { name: "Confirm new e-mail" });
    expect(confirmBtn).toBeDisabled();
    await userEvent.type(screen.getByLabelText("6-digit code"), "12ab3456");
    expect(screen.getByLabelText("6-digit code")).toHaveValue("123456");
    await userEvent.click(confirmBtn);
    await waitFor(() => expect(confirm).toHaveBeenCalledWith("tok", "123456"));
    expect(await screen.findByText(/Your sign-in e-mail was changed/)).toBeInTheDocument();
    expect(p).toHaveBeenCalled();
  });
  it("shows a wrong-code message from the server", async () => {
    vi.spyOn(api, "myProfile").mockResolvedValue(prof({ pending_email: { email: "new@example.com", expires_at: "x" } }));
    vi.spyOn(api, "confirmEmailChange").mockRejectedValue(new Error("That code is not right. You have 4 tries left."));
    at("/profile", <ProfilePage />);
    await userEvent.type(await screen.findByLabelText("6-digit code"), "000000");
    await userEvent.click(screen.getByRole("button", { name: "Confirm new e-mail" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("4 tries left");
  });
  it("checks the picture type and size before uploading, then uploads and removes", async () => {
    vi.spyOn(api, "myProfile").mockResolvedValue(prof());
    vi.spyOn(api, "myPicture").mockResolvedValue({ blob: new Blob(["x"]), filename: "a.jpg" });
    const up = vi.spyOn(api, "uploadMyPicture").mockResolvedValue(prof({ has_picture: true, picture_version: 1 }));
    const rm = vi.spyOn(api, "removeMyPicture").mockResolvedValue(prof());
    at("/profile", <ProfilePage />);
    const input = await screen.findByLabelText("Upload picture");
    await userEvent.upload(input, new File(["x"], "a.gif", { type: "image/gif" }), { applyAccept: false });
    expect(await screen.findByRole("alert")).toHaveTextContent("JPEG, PNG or WebP");
    expect(up).not.toHaveBeenCalled();
    const big = new File(["x"], "big.png", { type: "image/png" }); Object.defineProperty(big, "size", { value: 4 * 1024 * 1024 });
    await userEvent.upload(screen.getByLabelText("Upload picture"), big);
    expect(await screen.findByRole("alert")).toHaveTextContent("bigger than 3 MB");
    await userEvent.upload(screen.getByLabelText("Upload picture"), new File(["x"], "me.png", { type: "image/png" }));
    await waitFor(() => expect(up).toHaveBeenCalled());
    expect(await screen.findByText("Your picture was saved.")).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "Remove picture" }));
    await waitFor(() => expect(rm).toHaveBeenCalled());
    expect(await screen.findByText("Your picture was removed.")).toBeInTheDocument();
  });
  it("changes the password only when the rules and the repeat match", async () => {
    vi.spyOn(api, "myProfile").mockResolvedValue(prof());
    const change = vi.spyOn(api, "changePassword").mockResolvedValue(null);
    at("/profile", <ProfilePage />);
    await userEvent.type(await screen.findByLabelText("Current password"), "old-pass-1");
    await userEvent.type(screen.getByLabelText("New password"), "short");
    await userEvent.type(screen.getByLabelText("New password again"), "short");
    await userEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("at least 8 characters");
    expect(change).not.toHaveBeenCalled();
    await userEvent.clear(screen.getByLabelText("New password")); await userEvent.type(screen.getByLabelText("New password"), "better-pass-2");
    await userEvent.clear(screen.getByLabelText("New password again")); await userEvent.type(screen.getByLabelText("New password again"), "different-3");
    await userEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("not the same");
    await userEvent.clear(screen.getByLabelText("New password again")); await userEvent.type(screen.getByLabelText("New password again"), "better-pass-2");
    await userEvent.click(screen.getByRole("button", { name: "Change password" }));
    await waitFor(() => expect(change).toHaveBeenCalledWith("tok", "old-pass-1", "better-pass-2"));
    expect(await screen.findByText("Your password was changed.")).toBeInTheDocument();
  });
});

describe("Settings", () => {
  it("has light, dark and system default, applies them at once and remembers", async () => {
    vi.spyOn(api, "mySettings").mockResolvedValue(sets());
    at("/settings", <SettingsPage />);
    await userEvent.click(await screen.findByLabelText(/Dark/));
    expect(document.documentElement.dataset.theme).toBe("dark"); expect(localStorage.getItem("mindsync_theme")).toBe("dark");
    await userEvent.click(screen.getByLabelText(/Light/));
    expect(document.documentElement.dataset.theme).toBe("light");
    await userEvent.click(screen.getByLabelText(/System default/));
    expect(document.documentElement.dataset.theme).toBeUndefined(); expect(screen.getByLabelText(/System default/)).toBeChecked();
  });
  it("starts with the saved theme selected", async () => {
    localStorage.setItem("mindsync_theme", "dark");
    vi.spyOn(api, "mySettings").mockResolvedValue(sets());
    at("/settings", <SettingsPage />);
    expect(await screen.findByLabelText(/Dark/)).toBeChecked();
  });
  it("offers only 30% and 35%, explains with the 10-day example, and saves", async () => {
    vi.spyOn(api, "mySettings").mockResolvedValue(sets({ timezone: "Europe/Copenhagen" }));
    const save = vi.spyOn(api, "saveMySettings").mockResolvedValue(sets({ remind_enabled: true, remind_percent: 35, timezone: "Europe/Copenhagen" }));
    at("/settings", <SettingsPage />);
    const sw = await screen.findByRole("switch", { name: /Remind me by e-mail/ });
    expect(sw).not.toBeChecked();
    expect(screen.getByLabelText("30%")).toBeDisabled();
    expect(screen.getByText(/10 days to finish a task, a 30% reminder arrives when 3 days remain/)).toBeInTheDocument();
    expect(screen.queryByLabelText("25%")).toBeNull(); expect(screen.queryByLabelText("40%")).toBeNull();
    const saveBtn = screen.getByRole("button", { name: "Save settings" });
    expect(saveBtn).toBeDisabled();
    await userEvent.click(sw);
    await userEvent.click(screen.getByLabelText("35%"));
    expect(screen.getByText(/a 35% reminder arrives when 3.5 days remain/)).toBeInTheDocument();
    await userEvent.click(saveBtn);
    await waitFor(() => expect(save).toHaveBeenCalledWith("tok", { remind_enabled: true, remind_percent: 35, timezone: "Europe/Copenhagen" }));
    expect(await screen.findByText("Your settings were saved.")).toBeInTheDocument();
  });
  it("tells the truth when no mail server is set up, and sends a test e-mail on request", async () => {
    vi.spyOn(api, "mySettings").mockResolvedValue(sets({ delivery: "demo" }));
    const test = vi.spyOn(api, "sendTestReminder").mockResolvedValue({ delivery: "demo", message: "saved as a file in backend/outbox" });
    at("/settings", <SettingsPage />);
    expect(await screen.findByText(/No mail server is set up on this computer yet/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Send me a test e-mail/ }));
    await waitFor(() => expect(test).toHaveBeenCalled());
    expect(await screen.findByText(/saved as a file/)).toBeInTheDocument();
  });
  it("hides the mail-server note when a real mail server is set up", async () => {
    vi.spyOn(api, "mySettings").mockResolvedValue(sets({ delivery: "email" }));
    at("/settings", <SettingsPage />);
    await screen.findByRole("switch");
    expect(screen.queryByText(/No mail server is set up/)).toBeNull();
  });
  it("lets the student pick a time zone", async () => {
    vi.spyOn(api, "mySettings").mockResolvedValue(sets());
    const save = vi.spyOn(api, "saveMySettings").mockResolvedValue(sets({ timezone: "Asia/Karachi" }));
    at("/settings", <SettingsPage />);
    const sel = await screen.findByLabelText("Time zone");
    await userEvent.selectOptions(sel, "Asia/Karachi");
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith("tok", expect.objectContaining({ timezone: "Asia/Karachi" })));
  });
});

describe("Account menu", () => {
  it("links to My Profile and Settings and keeps everything it had", () => {
    render(<MemoryRouter><AccountModal onClose={() => {}} /></MemoryRouter>);
    expect(screen.getByRole("link", { name: /My Profile/ })).toHaveAttribute("href", "/profile");
    expect(screen.getByRole("link", { name: /Settings/ })).toHaveAttribute("href", "/settings");
    expect(screen.getByRole("heading", { name: "Change password" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download my data" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Delete my account/ })).toBeInTheDocument();
  });
});

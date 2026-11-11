import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api, ApiError } from "../api";
import LoginPage from "../pages/LoginPage";
import ForgotPasswordPage from "../pages/ForgotPasswordPage";
import ResetPasswordPage from "../pages/ResetPasswordPage";
import AccountModal from "../components/AccountModal";
import { passwordRules } from "../passwordRules";

vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ login: vi.fn() }) }));
afterEach(() => vi.restoreAllMocks());

const at = (path, element, routePath = "/") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={routePath} element={element} />
        <Route path="/login" element={<div>LOGIN PAGE</div>} />
      </Routes>
    </MemoryRouter>
  );

describe("login page", () => {
  it("has a Forgot password link and a Show/Hide button for the password", async () => {
    at("/login", <LoginPage />, "/login");
    expect(screen.getByRole("link", { name: /forgot your password/i })).toHaveAttribute("href", "/forgot-password");
    const pw = screen.getByLabelText(/^password/i, { selector: "input" });
    expect(pw).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: "Show" }));
    expect(pw).toHaveAttribute("type", "text");
    await userEvent.click(screen.getByRole("button", { name: "Hide" }));
    expect(pw).toHaveAttribute("type", "password");
  });
});

describe("forgot password page", () => {
  it("rejects an obviously wrong address without calling the server", async () => {
    const spy = vi.spyOn(api, "forgotPassword");
    at("/forgot-password", <ForgotPasswordPage />, "/forgot-password");
    await userEvent.type(screen.getByLabelText("Email"), "not-an-email");
    await userEvent.click(screen.getByRole("button", { name: /send me the link/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/does not look like an email/i);
    expect(spy).not.toHaveBeenCalled();
  });
  it("shows the server's neutral answer, and the demo-mode note when no mail server is set up", async () => {
    vi.spyOn(api, "forgotPassword").mockResolvedValue({ message: "If that address has a MindSync account, we have sent a link.", delivery: "demo" });
    at("/forgot-password", <ForgotPasswordPage />, "/forgot-password");
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.click(screen.getByRole("button", { name: /send me the link/i }));
    expect(await screen.findByText(/If that address has a MindSync account/)).toBeInTheDocument();
    expect(screen.getByText(/cannot send real emails yet/i)).toBeInTheDocument();
    expect(api.forgotPassword).toHaveBeenCalledWith("a@b.com");
  });
  it("shows a too-many-requests message from the server", async () => {
    vi.spyOn(api, "forgotPassword").mockRejectedValue(new ApiError("Too many password-reset requests. Please try again later.", 429));
    at("/forgot-password", <ForgotPasswordPage />, "/forgot-password");
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.click(screen.getByRole("button", { name: /send me the link/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/too many/i);
  });
});

describe("reset password page", () => {
  it("explains what to do when the link has no token", () => {
    at("/reset-password", <ResetPasswordPage />, "/reset-password");
    expect(screen.getByRole("alert")).toHaveTextContent(/only works from the link in your email/i);
  });
  it("checks the two passwords match before calling the server", async () => {
    const spy = vi.spyOn(api, "resetPassword");
    at("/reset-password?token=" + "a".repeat(43), <ResetPasswordPage />, "/reset-password");
    await userEvent.type(screen.getByLabelText("New password"), "Good-pass-1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "Different-1");
    await userEvent.click(screen.getByRole("button", { name: /save new password/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/do not match/i);
    expect(spy).not.toHaveBeenCalled();
  });
  it("refuses a weak password locally", async () => {
    const spy = vi.spyOn(api, "resetPassword");
    at("/reset-password?token=" + "a".repeat(43), <ResetPasswordPage />, "/reset-password");
    await userEvent.type(screen.getByLabelText("New password"), "onlyletters");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "onlyletters");
    await userEvent.click(screen.getByRole("button", { name: /save new password/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/does not follow all the rules/i);
    expect(spy).not.toHaveBeenCalled();
  });
  it("sends the token and new password, then goes to the login page", async () => {
    const token = "b".repeat(43);
    vi.spyOn(api, "resetPassword").mockResolvedValue({ message: "Your password was changed. You can now log in with it." });
    at("/reset-password?token=" + token, <ResetPasswordPage />, "/reset-password");
    await userEvent.type(screen.getByLabelText("New password"), "Good-pass-1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "Good-pass-1");
    await userEvent.click(screen.getByRole("button", { name: /save new password/i }));
    await waitFor(() => expect(api.resetPassword).toHaveBeenCalledWith(token, "Good-pass-1"));
    expect(await screen.findByText("LOGIN PAGE")).toBeInTheDocument();
  });
  it("offers a new link when the server says this one is expired", async () => {
    vi.spyOn(api, "resetPassword").mockRejectedValue(new ApiError("This reset link is not valid or has expired. Please ask for a new one.", 400));
    at("/reset-password?token=" + "c".repeat(43), <ResetPasswordPage />, "/reset-password");
    await userEvent.type(screen.getByLabelText("New password"), "Good-pass-1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "Good-pass-1");
    await userEvent.click(screen.getByRole("button", { name: /save new password/i }));
    expect(await screen.findByRole("link", { name: /ask for a new link/i })).toHaveAttribute("href", "/forgot-password");
  });
});

vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ token: "tok", user: { email: "a@b.com", display_name: "Abi" }, logout: vi.fn(), refreshUser: vi.fn() }) }));

describe("change password in the account window", () => {
  it("sends the current and the new password", async () => {
    const spy = vi.spyOn(api, "changePassword").mockResolvedValue(null);
    render(<AccountModal onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText("Current password"), "Old-pass-1");
    const news = screen.getAllByLabelText(/^New password/);
    await userEvent.type(news[0], "New-pass-22");
    await userEvent.type(news[1], "New-pass-22");
    await userEvent.click(screen.getByRole("button", { name: "Change password" }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("tok", "Old-pass-1", "New-pass-22"));
    expect(await screen.findByText("Your password was changed.")).toBeInTheDocument();
  });
  it("shows the server's message when the current password is wrong", async () => {
    vi.spyOn(api, "changePassword").mockRejectedValue(new Error("Your current password is not correct."));
    render(<AccountModal onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText("Current password"), "wrong");
    const news = screen.getAllByLabelText(/^New password/);
    await userEvent.type(news[0], "New-pass-22");
    await userEvent.type(news[1], "New-pass-22");
    await userEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Your current password is not correct.");
  });
  it("does not send a weak password", async () => {
    const spy = vi.spyOn(api, "changePassword").mockResolvedValue(null);
    render(<AccountModal onClose={() => {}} />);
    await userEvent.type(screen.getByLabelText("Current password"), "Old-pass-1");
    const news = screen.getAllByLabelText(/^New password/);
    await userEvent.type(news[0], "short");
    await userEvent.type(news[1], "short");
    await userEvent.click(screen.getByRole("button", { name: "Change password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/at least 8 characters/);
    expect(spy).not.toHaveBeenCalled();
  });
});

describe("password rules helper", () => {
  it("flags missing letters, numbers and length", () => {
    expect(passwordRules("abc").filter((r) => !r.ok)).toHaveLength(2);
    expect(passwordRules("Good-pass-1").every((r) => r.ok)).toBe(true);
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "../api";
import DashboardPage from "../pages/DashboardPage";
import PlannerPage from "../pages/PlannerPage";
import AiZonePage from "../pages/AiZonePage";
import NotebookPage from "../pages/NotebookPage";

vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ token: "tok", user: { email: "a@b.com", display_name: "Abi" } }) }));
afterEach(() => vi.restoreAllMocks());

const at = (path, el, route = path.split("?")[0]) =>
  render(<MemoryRouter initialEntries={[path]}><Routes><Route path={route} element={el} /></Routes></MemoryRouter>);

const dash = (over = {}) => ({
  total: 4, completed: 1, remaining: 3, progress: 25, today: "2026-10-30", note: "",
  deadlines: [{ plan_id: "p1", subject: "Biology", topic: "Cells", target_date: "2027-03-05", left: 3, total: 4 }],
  overdue: [{ id: "t9", title: "Late task", subject: "Biology", due_date: "2026-10-28", days_late: 2 }],
  tasks: [
    { id: "t1", title: "Read chapter", subject: "Biology", due_date: "2026-10-30", start_time: "18:00", minutes: 30, done: false },
    { id: "t2", title: "Make notes", subject: "Biology", due_date: "2026-10-31", start_time: null, minutes: 45, done: true },
  ],
  ...over,
});

describe("Dashboard", () => {
  it("shows the numbers, the progress bar, deadlines and overdue tasks", async () => {
    vi.spyOn(api, "dashboard").mockResolvedValue(dash());
    at("/dashboard", <DashboardPage />);
    expect(await screen.findByTestId("total")).toHaveTextContent("4");
    expect(screen.getByTestId("completed")).toHaveTextContent("1");
    expect(screen.getByTestId("remaining")).toHaveTextContent("3");
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "25");
    expect(screen.getByText(/Biology: Cells/)).toBeInTheDocument();
    expect(screen.getByText("Late task")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Create Study Plan" })).toHaveAttribute("href", "/planner");
  });
  it("ticking a task saves it and reloads the numbers", async () => {
    const d = vi.spyOn(api, "dashboard").mockResolvedValueOnce(dash()).mockResolvedValue(dash({ completed: 2, remaining: 2, progress: 50 }));
    const edit = vi.spyOn(api, "editTask").mockResolvedValue({});
    at("/dashboard", <DashboardPage />);
    await userEvent.click(await screen.findByRole("checkbox", { name: /Mark as done: Read chapter/ }));
    await waitFor(() => expect(edit).toHaveBeenCalledWith("tok", "t1", { done: true }));
    await waitFor(() => expect(screen.getByTestId("completed")).toHaveTextContent("2"));
    expect(d).toHaveBeenCalledTimes(2);
  });
  it("says so when there are no tasks", async () => {
    vi.spyOn(api, "dashboard").mockResolvedValue(dash({ total: 0, completed: 0, remaining: 0, progress: 0, tasks: [], deadlines: [], overdue: [] }));
    at("/dashboard", <DashboardPage />);
    expect(await screen.findByText(/You have no tasks yet/)).toBeInTheDocument();
  });
});

describe("Study Planner", () => {
  it("has the six fields and one button, and sends them", async () => {
    vi.spyOn(api, "plans").mockResolvedValue({ plans: [] });
    const create = vi.spyOn(api, "createPlan").mockResolvedValue({ id: "p1", subject: "Maths", topic: "Algebra", total: 5, note: "Made offline.", roadmap: [], tasks: [], done: 0, target_date: "2027-03-05", source: "offline" });
    at("/planner", <PlannerPage />);
    const btn = screen.getByRole("button", { name: "Generate My Study Plan" });
    expect(btn).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Subject Name"), "Maths");
    await userEvent.type(screen.getByLabelText(/Topic Name/), "Algebra");
    await userEvent.type(screen.getByLabelText(/Learning Goal/), "I want to pass.");
    await userEvent.type(screen.getByLabelText("Target Completion Date"), "2027-03-05");
    await userEvent.click(screen.getByLabelText("Tired"));
    await userEvent.click(screen.getByLabelText("High"));
    await userEvent.click(btn);
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create.mock.calls[0][1]).toMatchObject({ subject: "Maths", topic: "Algebra", goal: "I want to pass.", target_date: "2027-03-05", mood: "tired", stress: "high" });
    expect(await screen.findByText(/Your plan is ready/)).toBeInTheDocument();
  });
  it("tells students what is sent to the AI service, and that mood and stress are not", async () => {
    vi.spyOn(api, "plans").mockResolvedValue({ plans: [] });
    at("/planner", <PlannerPage />);
    const note = screen.getByText(/subject, topic and learning goal are sent to the AI service/);
    expect(note).toHaveTextContent(/mood and stress answers stay in MindSync and are never sent/);
  });
  it("shows a clear message when the plan cannot be made", async () => {
    vi.spyOn(api, "plans").mockResolvedValue({ plans: [] });
    vi.spyOn(api, "createPlan").mockRejectedValue(new Error("Please wait a minute before making another plan."));
    at("/planner", <PlannerPage />);
    await userEvent.type(screen.getByLabelText("Subject Name"), "Maths");
    await userEvent.type(screen.getByLabelText(/Topic Name/), "Algebra");
    await userEvent.type(screen.getByLabelText("Target Completion Date"), "2027-03-05");
    await userEvent.click(screen.getByRole("button", { name: "Generate My Study Plan" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Please wait a minute");
  });
});

describe("AI Learning Zone", () => {
  it("is honest when the AI is off: no quiz can be generated", async () => {
    vi.spyOn(api, "studioStatus").mockResolvedValue({ ai_available: false, limits: {} });
    at("/ai-zone", <AiZonePage />);
    expect(await screen.findByText("The AI quiz is not available right now")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate Quiz" })).toBeDisabled();
  });
  it("reads a Notebook document when opened with ?document=", async () => {
    vi.spyOn(api, "studioStatus").mockResolvedValue({ ai_available: true, limits: { min_chars: 300, max_chars: 24000 } });
    const text = vi.spyOn(api, "documentText").mockResolvedValue({ name: "bio.pdf", text: "x".repeat(900), chars: 900 });
    at("/ai-zone?document=d1", <AiZonePage />, "/ai-zone");
    await waitFor(() => expect(text).toHaveBeenCalledWith("tok", "d1"));
    expect(await screen.findByText(/900 characters read/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate Quiz" })).toBeEnabled();
  });
  it("refuses a document that is too short", async () => {
    vi.spyOn(api, "studioStatus").mockResolvedValue({ ai_available: true, limits: { min_chars: 300, max_chars: 24000 } });
    vi.spyOn(api, "documentText").mockResolvedValue({ name: "tiny.txt", text: "short", chars: 5 });
    at("/ai-zone?document=d2", <AiZonePage />, "/ai-zone");
    expect(await screen.findByText(/too short for a quiz/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate Quiz" })).toBeDisabled();
  });
});

describe("My Notebook", () => {
  beforeEach(() => {
    vi.spyOn(api, "notes").mockResolvedValue({ notes: [{ id: "n1", title: "Cells", preview: "Cells are small", updated_at: "2026-10-30T10:00:00" }] });
    vi.spyOn(api, "documents").mockResolvedValue({ max_mb: 10, types: [".pdf"], documents: [{ id: "d1", name: "bio.pdf", ext: ".pdf", size: 2048, created_at: "2026-10-30T10:00:00" }] });
  });
  it("lists notes, opens one, saves an edit", async () => {
    vi.spyOn(api, "note").mockResolvedValue({ id: "n1", title: "Cells", body: "Cells are small" });
    const edit = vi.spyOn(api, "editNote").mockResolvedValue({ id: "n1", title: "Cells", body: "Cells are small and many" });
    at("/notebook", <NotebookPage />);
    await userEvent.click(await screen.findByRole("button", { name: /Cells/ }));
    const box = await screen.findByLabelText("Your note");
    await userEvent.type(box, " and many");
    await userEvent.click(screen.getByRole("button", { name: "Save note" }));
    await waitFor(() => expect(edit).toHaveBeenCalledWith("tok", "n1", { title: "Cells", body: "Cells are small and many" }));
    expect(await screen.findByText("Saved to your account.")).toBeInTheDocument();
  });
  it("creates a new note and needs a title", async () => {
    const create = vi.spyOn(api, "createNote").mockResolvedValue({ id: "n2", title: "New", body: "Hello" });
    at("/notebook", <NotebookPage />);
    await userEvent.click(await screen.findByRole("button", { name: "New note" }));
    await userEvent.type(screen.getByLabelText("Your note"), "Hello");
    await userEvent.click(screen.getByRole("button", { name: "Save note" }));
    expect(create).not.toHaveBeenCalled();                    // the title box is required
    await userEvent.type(screen.getByLabelText("Title"), "New");
    await userEvent.click(screen.getByRole("button", { name: "Save note" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith("tok", { title: "New", body: "Hello" }));
  });
  it("searches notes", async () => {
    at("/notebook", <NotebookPage />);
    await userEvent.type(await screen.findByPlaceholderText("Search my notes"), "cell");
    await waitFor(() => expect(api.notes).toHaveBeenCalledWith("tok", "cell"));
  });
  it("shows My Documents with a Create Quiz link to the AI Learning Zone", async () => {
    at("/notebook?tab=documents", <NotebookPage />, "/notebook");
    const row = (await screen.findByText("bio.pdf")).closest("li");
    expect(within(row).getByRole("link", { name: "Create Quiz" })).toHaveAttribute("href", "/ai-zone?document=d1");
    for (const n of ["View", "Download", "Rename", "Delete"]) expect(within(row).getByRole("button", { name: n })).toBeInTheDocument();
  });
  it("asks before deleting a document", async () => {
    const del = vi.spyOn(api, "deleteDocument").mockResolvedValue(null);
    at("/notebook?tab=documents", <NotebookPage />, "/notebook");
    const row = (await screen.findByText("bio.pdf")).closest("li");
    await userEvent.click(within(row).getByRole("button", { name: "Delete" }));
    expect(del).not.toHaveBeenCalled();
    await userEvent.click(within(row).getByRole("button", { name: "Yes, delete" }));
    await waitFor(() => expect(del).toHaveBeenCalledWith("tok", "d1"));
  });
});

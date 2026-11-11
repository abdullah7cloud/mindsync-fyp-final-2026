import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../context/AuthContext";
import LandingPage from "../pages/LandingPage";

function renderLanding() {
  return render(<MemoryRouter><AuthProvider><LandingPage /></AuthProvider></MemoryRouter>);
}

describe("welcome page", () => {
  it("has a clear headline, one sentence about MindSync and a Get Started button", () => {
    renderLanding();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Study Smarter. Feel Better.");
    expect(screen.getByText("Plan your studies, stay organized, and feel more in control of your day.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Get Started" })[0]).toHaveAttribute("href", "/register");
  });
  it("shows four benefits and three steps", () => {
    renderLanding();
    const benefits = screen.getByRole("heading", { name: "How MindSync helps" }).closest("section");
    expect(benefits.querySelectorAll("article")).toHaveLength(4);
    expect(document.querySelectorAll(".lp-steps li")).toHaveLength(3);
  });
  it("shows photos with real descriptions (alt text) and no technical jargon", () => {
    renderLanding();
    const imgs = [...document.querySelectorAll("img.photo")];
    expect(imgs.length).toBeGreaterThanOrEqual(4);
    for (const img of imgs) {
      expect(img.getAttribute("alt").length).toBeGreaterThan(15);
      expect(img.getAttribute("srcset")).toMatch(/\.webp \d+w/);
    }
    const text = document.body.textContent;
    for (const jargon of ["logistic", "Argon2", "heuristic", "Burnout Mode", "ranking"]) expect(text).not.toMatch(new RegExp(jargon, "i"));
  });
  it("has a full-width hero photo with a dark overlay behind the words", () => {
    renderLanding();
    const hero = document.querySelector(".lp-hero");
    expect(hero.querySelector("img.lp-hero-img")).not.toBeNull();
    expect(hero.querySelector(".lp-hero-shade")).not.toBeNull();
    expect(hero.querySelector("img.lp-hero-img").getAttribute("fetchpriority")).toBe("high");
    expect(hero.querySelector("img.lp-hero-img").getAttribute("srcset")).toMatch(/1920w/);
  });
  it("credits the photographers and says the people shown do not endorse MindSync", () => {
    renderLanding();
    const foot = document.querySelector(".lp-footer").textContent;
    for (const name of ["Eliott Reyna", "Brooke Cagle", "Meredith Spencer", "Zoshua Colah", "Good Faces"]) expect(foot).toContain(name);
    expect(foot).toMatch(/do not endorse/i);
  });
  it("does not claim to diagnose, and is honest that AI may be used", () => {
    renderLanding();
    expect(screen.getByText(/cannot diagnose anything/)).toBeInTheDocument();
    expect(screen.getByText(/goes to that AI service/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/No outside AI|No sign-up needed|as a guest/i);
  });
  it("has no links to pages that no longer exist", () => {
    renderLanding();
    const hrefs = [...document.querySelectorAll("a[href]")].map((a) => a.getAttribute("href")).filter((h) => h.startsWith("/"));
    for (const h of hrefs) expect(["/", "/login", "/register", "/dashboard", "/planner"]).toContain(h);
  });
});

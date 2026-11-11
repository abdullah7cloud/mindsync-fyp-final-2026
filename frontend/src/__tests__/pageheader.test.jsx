import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import PageHeader from "../components/PageHeader";

describe("page header", () => {
  it("shows a photo banner with a dark overlay and readable text on pages with a photo", () => {
    const { container } = render(
      <PageHeader title="My Progress" subtitle="See how you are doing." start="Look at the numbers."
        image={{ name: "progress", side: "left", focus: "50% 56%", alt: "A delighted student outside an old university building" }} />
    );
    expect(screen.getByRole("heading", { level: 1, name: "My Progress" })).toBeInTheDocument();
    const banner = container.querySelector(".page-banner");
    expect(banner).not.toBeNull();
    expect(banner.querySelector(".banner-shade")).not.toBeNull();
    const img = banner.querySelector("img");
    expect(img.getAttribute("alt")).toMatch(/student/);
    expect(img.getAttribute("srcset")).toMatch(/640w/);
    expect(img.style.objectPosition).toBe("50% 56%");
    expect(screen.getByText("Start here")).toBeInTheDocument();
  });
  it("is plain text only (no photo) on pages that hold forms and lists", () => {
    const { container } = render(<PageHeader title="My Tasks" subtitle="Everything you need to do." />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector(".page-banner")).toBeNull();
  });
});

import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Remove rendered components and the fake browser storage between tests so they cannot affect each other.
afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
});

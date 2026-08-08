import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PriorityBadge } from "../PriorityBadge";

describe("PriorityBadge", () => {
  it.each([
    ["rojo", "🔴"],
    ["amarillo", "🟡"],
    ["verde", "🟢"],
  ] as const)("renderiza el emoji correcto para prioridad %s", (priority, emoji) => {
    render(<PriorityBadge priority={priority} />);
    expect(screen.getByText(emoji)).toBeInTheDocument();
  });

  it("expone la prioridad en el title para accesibilidad", () => {
    render(<PriorityBadge priority="rojo" />);
    expect(screen.getByTitle("Prioridad: rojo")).toBeInTheDocument();
  });
});

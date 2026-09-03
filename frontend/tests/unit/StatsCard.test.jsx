import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import StatsCard from "../../src/components/StatsCard.jsx";

describe("StatsCard", () => {
  it("renders the label and value", () => {
    render(<StatsCard label="Torneos activos" value={3} />);
    expect(screen.getByText("Torneos activos")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("renders a positive weekly variation with a + sign", () => {
    render(<StatsCard label="Torneos activos" value={3} delta={1} />);
    expect(screen.getByText("+1")).toBeInTheDocument();
  });

  it("renders a negative weekly variation with a - sign", () => {
    render(<StatsCard label="Torneos activos" value={1} delta={-2} />);
    // -2 already carries its own minus sign from the number.
    expect(screen.getByText("-2")).toBeInTheDocument();
  });

  it("renders a zero variation without a sign", () => {
    render(<StatsCard label="Torneos activos" value={3} delta={0} />);
    expect(screen.getByText("0")).toBeInTheDocument();
    // No signed token is rendered for a neutral delta.
    expect(screen.queryByText("+0")).toBeNull();
    expect(screen.queryByText("-0")).toBeNull();
  });

  it("renders no variation token when delta is null/neutral", () => {
    render(<StatsCard label="Torneos activos" value={0} delta={null} />);
    expect(screen.queryByText("+0")).toBeNull();
    expect(screen.queryByText(/^[+-]/)).toBeNull();
  });

  it("renders winrate 0% without breaking when there are no games", () => {
    render(<StatsCard label="Victorias" value={0} subvalue="0%" />);
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("renders a winrate subvalue alongside the wins value", () => {
    render(<StatsCard label="Victorias" value={12} subvalue="60%" />);
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
  });
});

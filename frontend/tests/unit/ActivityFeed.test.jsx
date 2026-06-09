import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import ActivityFeed from "../../src/components/ActivityFeed.jsx";

function renderFeed(events) {
  return render(
    <MemoryRouter>
      <ActivityFeed events={events} />
    </MemoryRouter>,
  );
}

const NOW = "2026-06-09T12:00:00Z";

function ev(overrides = {}) {
  return {
    id: overrides.id ?? crypto.randomUUID(),
    event_type: overrides.event_type ?? "MATCH_WIN",
    created_at: overrides.created_at ?? NOW,
    actor: overrides.actor ?? { id: "u1", nickname: "playerB", avatar_url: null, exists: true },
    tournament:
      overrides.tournament === undefined
        ? { id: "t1", name: "Spring Cup" }
        : overrides.tournament,
  };
}

describe("ActivityFeed", () => {
  it("renders each event type with actor, action and tournament", () => {
    const events = [
      ev({ id: "1", event_type: "MATCH_WIN" }),
      ev({ id: "2", event_type: "TOURNAMENT_JOIN" }),
      ev({ id: "3", event_type: "TOURNAMENT_INVITE" }),
      ev({ id: "4", event_type: "TOURNAMENT_CREATE" }),
    ];
    renderFeed(events);

    // Actor appears for every event.
    expect(screen.getAllByText("playerB").length).toBe(4);
    // Tournament name appears for every event.
    expect(screen.getAllByText("Spring Cup").length).toBe(4);
  });

  it("links the actor to /users/:nickname and the tournament to /tournaments/:id", () => {
    renderFeed([ev({ id: "1", event_type: "MATCH_WIN" })]);

    const actorLink = screen.getByRole("link", { name: /playerB/i });
    expect(actorLink).toHaveAttribute("href", "/users/playerB");

    const tournamentLink = screen.getByRole("link", { name: /Spring Cup/i });
    expect(tournamentLink).toHaveAttribute("href", "/tournaments/t1");
  });

  it("renders a relative time for the event", () => {
    renderFeed([ev({ id: "1", created_at: new Date().toISOString() })]);
    // The client formats relative time; "ahora"/"hace" must appear.
    expect(screen.getByText(/ahora|hace/i)).toBeInTheDocument();
  });

  it("renders a resilient entry without a tournament link when tournament is null", () => {
    renderFeed([ev({ id: "1", event_type: "TOURNAMENT_JOIN", tournament: null })]);
    // No tournament link, and no crash.
    expect(screen.queryByRole("link", { name: /Spring Cup/i })).toBeNull();
    // Actor still shows.
    expect(screen.getByText("playerB")).toBeInTheDocument();
  });

  it("renders the actor as plain text (no link) when the actor no longer exists", () => {
    renderFeed([
      ev({
        id: "1",
        event_type: "MATCH_WIN",
        actor: { id: null, nickname: "deletedUser", avatar_url: null, exists: false },
      }),
    ]);
    expect(screen.queryByRole("link", { name: /deletedUser/i })).toBeNull();
    expect(screen.getByText("deletedUser")).toBeInTheDocument();
  });

  it("shows an informative empty state when there are no events", () => {
    renderFeed([]);
    expect(screen.getByText(/sin actividad|no hay actividad/i)).toBeInTheDocument();
  });
});

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProfileForm from "../../src/components/ProfileForm.jsx";
import { resetProfileMockState, seedProfile } from "../mocks/profileHandlers.js";

const baseProfile = {
  id: "00000000-0000-0000-0000-000000000001",
  nickname: "alice",
  email: "alice@example.com",
  avatar_url: null,
  linked_games: [],
  lol_stats: null,
};

describe("ProfileForm", () => {
  beforeEach(() => {
    resetProfileMockState();
    seedProfile(baseProfile);
  });

  it("submits nickname change and shows success", async () => {
    const onUpdated = vi.fn();
    const user = userEvent.setup();
    render(<ProfileForm profile={baseProfile} onUpdated={onUpdated} />);

    const input = screen.getByLabelText("Nickname");
    await user.clear(input);
    await user.type(input, "alicenew");
    await user.click(screen.getByRole("button", { name: "Guardar nickname" }));

    expect(await screen.findByText("Nickname actualizado")).toBeInTheDocument();
    expect(onUpdated).toHaveBeenCalled();
  });

  it("shows error message on 409 nickname conflict", async () => {
    const user = userEvent.setup();
    render(<ProfileForm profile={baseProfile} onUpdated={vi.fn()} />);

    const input = screen.getByLabelText("Nickname");
    await user.clear(input);
    await user.type(input, "taken");
    await user.click(screen.getByRole("button", { name: "Guardar nickname" }));

    expect(await screen.findByText("Nickname no disponible")).toBeInTheDocument();
  });
});

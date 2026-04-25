import { setupServer } from "msw/node";
import { authHandlers } from "./authHandlers.js";
import { tournamentHandlers } from "./tournamentHandlers.js";
import { matchHandlers } from "./matchHandlers.js";

export const server = setupServer(...authHandlers, ...tournamentHandlers, ...matchHandlers);

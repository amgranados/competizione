import { setupServer } from "msw/node";
import { authHandlers } from "./authHandlers.js";
import { tournamentHandlers } from "./tournamentHandlers.js";
import { matchHandlers } from "./matchHandlers.js";
import { profileHandlers } from "./profileHandlers.js";
import { friendsHandlers } from "./friendsHandlers.js";
import { dashboardHandlers } from "./dashboardHandlers.js";

export const server = setupServer(
  ...authHandlers,
  ...tournamentHandlers,
  ...matchHandlers,
  ...profileHandlers,
  ...friendsHandlers,
  ...dashboardHandlers,
);

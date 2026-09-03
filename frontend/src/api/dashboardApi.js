import { request } from "./authApi.js";

export const dashboardApi = {
  getDashboard: () => request("/api/dashboard"),
};

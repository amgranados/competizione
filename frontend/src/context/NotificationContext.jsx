import { createContext, useCallback, useContext } from "react";
import { usePolling } from "../hooks/usePolling.js";
import { notificationApi } from "../api/notificationApi.js";

export const NotificationContext = createContext(null);

export function NotificationProvider({ children, intervalMs = 10000 }) {
  const { data, error, refresh } = usePolling(() => notificationApi.list(), intervalMs);

  const markRead = useCallback(async (id) => {
    await notificationApi.markRead(id);
    await refresh();
  }, [refresh]);

  const value = {
    notifications: data ?? [],
    error,
    markRead,
    refresh,
  };
  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error("useNotifications must be used within <NotificationProvider>");
  }
  return ctx;
}

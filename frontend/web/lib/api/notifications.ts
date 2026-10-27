import { api } from "@/lib/api";

export type NotificationList = {
  items: { id: string; read_at: string | null; payload: { title: string; url: string } }[];
  unread_count: number;
};

// ProtectedShell gives each authenticated user a separate QueryClient and
// destroys it on logout. Header and dashboard share this complete response.
export const notificationQueryKey = ["notifications"] as const;
export const getNotifications = () => api<NotificationList>("/notifications");

import { z } from "zod";

export const healthSchema = z.object({
  status: z.enum(["ok", "degraded"]),
  services: z.record(z.string(), z.enum(["ok", "unavailable"])),
});

export type Health = z.infer<typeof healthSchema>;

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch(`${apiBaseUrl}/health/ready`, {
    signal,
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  const data: unknown = await response.json();
  const parsed = healthSchema.safeParse(data);
  if (!parsed.success) {
    throw new Error("Invalid health response from API");
  }
  if (!response.ok && response.status !== 503) {
    throw new Error(`API returned ${response.status}`);
  }
  return parsed.data;
}

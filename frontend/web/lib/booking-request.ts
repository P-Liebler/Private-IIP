// Opaque request ID only: no credentials or financial drafts in URL/storage.
// Keep it after an uncertain network result; clear only after a confirmed response.
export function bookingRequestKey(scope: string): string {
  const url = new URL(window.location.href);
  const field = `request_${scope}`;
  const existing = url.searchParams.get(field);
  if (existing && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(existing)) return existing;
  const key = crypto.randomUUID();
  url.searchParams.set(field, key);
  window.history.replaceState(null, "", url);
  return key;
}

export function clearBookingRequestKey(scope: string) {
  const url = new URL(window.location.href);
  url.searchParams.delete(`request_${scope}`);
  window.history.replaceState(null, "", url);
}

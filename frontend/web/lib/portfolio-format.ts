export function money(value: string | null | undefined, currency: string) {
  return value === null || value === undefined ? "DATA_UNAVAILABLE" :
    `${Number(value).toLocaleString("de-CH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}
export function ratio(value: string | null | undefined) {
  return value === null || value === undefined ? "DATA_UNAVAILABLE" : `${(Number(value) * 100).toFixed(2)} %`;
}

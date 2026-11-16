export function money(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

export function compact(value: number, digits = 1) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value);
}

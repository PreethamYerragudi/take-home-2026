export function formatPrice(price: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
    }).format(price)
  } catch {
    return `${currency} ${price.toFixed(2)}`
  }
}

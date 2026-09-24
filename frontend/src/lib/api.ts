import type { Product, ProductSummary } from "@/types"

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`Request to ${url} failed: ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export function fetchProducts(): Promise<ProductSummary[]> {
  return getJson<ProductSummary[]>("/api/products")
}

export function fetchProduct(slug: string): Promise<Product> {
  return getJson<Product>(`/api/products/${encodeURIComponent(slug)}`)
}

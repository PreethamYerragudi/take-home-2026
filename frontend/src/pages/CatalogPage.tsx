import { useEffect, useState } from "react"

import { ProductCard } from "@/components/ProductCard"
import { Skeleton } from "@/components/ui/skeleton"
import { fetchProducts } from "@/lib/api"
import type { ProductSummary } from "@/types"

export function CatalogPage() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold">Catalog</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {products
            ? `${products.length} product${products.length === 1 ? "" : "s"}`
            : "Loading products…"}
        </p>
      </header>

      {error && (
        <p className="text-sm text-destructive">
          Failed to load products: {error}
        </p>
      )}

      {!error && (
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 lg:grid-cols-4">
          {products
            ? products.map((product) => (
                <ProductCard key={product.slug} product={product} />
              ))
            : Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="aspect-square w-full rounded-xl" />
              ))}
        </div>
      )}
    </div>
  )
}

import { ArrowLeft, Check, ChevronRight } from "lucide-react"
import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"

import { AspectRatio } from "@/components/ui/aspect-ratio"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { fetchProduct } from "@/lib/api"
import { formatPrice } from "@/lib/format"
import { productImageTransitionName } from "@/lib/utils"
import type { Product } from "@/types"

function BackLink() {
  return (
    <Link
      to="/"
      viewTransition
      className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" />
      Back to catalog
    </Link>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
      {children}
    </h2>
  )
}

export function ProductPage() {
  const { slug } = useParams<{ slug: string }>()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeImage, setActiveImage] = useState(0)

  useEffect(() => {
    if (!slug) return
    setProduct(null)
    setError(null)
    setActiveImage(0)
    fetchProduct(slug)
      .then(setProduct)
      .catch((e: Error) => setError(e.message))
  }, [slug])

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10">
        <BackLink />
        <p className="mt-6 text-sm text-destructive">
          Failed to load product: {error}
        </p>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <BackLink />
        <div className="mt-6 grid gap-10 md:grid-cols-2">
          <Skeleton className="aspect-square w-full rounded-xl" />
          <div className="space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-6 w-32" />
          </div>
        </div>
      </div>
    )
  }

  const onSale =
    product.price.compare_at_price != null &&
    product.price.compare_at_price > product.price.price

  const discountPct = onSale
    ? Math.round(
        (1 -
          product.price.price /
            (product.price.compare_at_price as number)) *
          100
      )
    : 0

  const categoryParts = product.category.name.split(" > ")

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <BackLink />

      <div className="mt-6 grid gap-12 md:grid-cols-2">
        <div>
          <AspectRatio
            ratio={1}
            className="overflow-hidden rounded-2xl bg-muted ring-1 ring-foreground/10"
          >
            {product.image_urls.length > 0 ? (
              <img
                src={product.image_urls[activeImage]}
                alt={product.name}
                className="absolute inset-0 h-full w-full object-cover"
                style={
                  slug && activeImage === 0
                    ? { viewTransitionName: productImageTransitionName(slug) }
                    : undefined
                }
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
                No image available
              </div>
            )}
          </AspectRatio>

          {product.image_urls.length > 1 && (
            <div className="mt-3 grid grid-cols-6 gap-2">
              {product.image_urls.map((url, i) => (
                <button
                  key={url}
                  type="button"
                  onClick={() => setActiveImage(i)}
                  aria-label={`Show image ${i + 1}`}
                  className={`overflow-hidden rounded-lg ring-1 transition ${
                    i === activeImage
                      ? "ring-2 ring-primary"
                      : "opacity-70 ring-foreground/10 hover:opacity-100 hover:ring-foreground/30"
                  }`}
                >
                  <AspectRatio ratio={1} className="bg-muted">
                    <img
                      src={url}
                      alt=""
                      className="absolute inset-0 h-full w-full object-cover"
                    />
                  </AspectRatio>
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="flex items-center gap-1.5 text-xs tracking-wide text-muted-foreground uppercase">
            {categoryParts.map((part, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <ChevronRight className="h-3 w-3 shrink-0" />}
                {part}
              </span>
            ))}
          </div>

          <p className="mt-3 text-sm font-medium text-muted-foreground">
            {product.brand}
          </p>
          <h1 className="mt-1 text-2xl leading-tight font-semibold text-balance">
            {product.name}
          </h1>

          <div className="mt-5 rounded-xl bg-muted/50 p-4 ring-1 ring-foreground/10">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="text-2xl font-semibold tracking-tight">
                {formatPrice(product.price.price, product.price.currency)}
              </span>
              {onSale && (
                <span className="text-sm text-muted-foreground line-through">
                  {formatPrice(
                    product.price.compare_at_price as number,
                    product.price.currency
                  )}
                </span>
              )}
              {onSale && (
                <Badge variant="destructive">Save {discountPct}%</Badge>
              )}
            </div>

            {product.colors.length > 0 && (
              <>
                <Separator className="my-4" />
                <SectionLabel>Colors</SectionLabel>
                <div className="mt-2 flex flex-wrap gap-2">
                  {product.colors.map((color) => (
                    <Badge key={color} variant="secondary">
                      {color}
                    </Badge>
                  ))}
                </div>
              </>
            )}
          </div>

          <div className="mt-6 space-y-2">
            <SectionLabel>Description</SectionLabel>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {product.description}
            </p>
          </div>

          {product.key_features.length > 0 && (
            <div className="mt-6 space-y-2">
              <SectionLabel>Key Features</SectionLabel>
              <ul className="mt-1 space-y-1.5">
                {product.key_features.map((feature, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm leading-relaxed text-muted-foreground"
                  >
                    <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-foreground/60" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {product.variants.length > 0 && (
            <div className="mt-6 space-y-2">
              <SectionLabel>
                Available Options ({product.variants.length})
              </SectionLabel>
              <div className="max-h-72 divide-y overflow-y-auto rounded-lg ring-1 ring-foreground/10">
                {product.variants.map((variant, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between gap-4 px-3 py-2 text-sm transition-colors hover:bg-muted/50"
                  >
                    <span>
                      {variant.options.map((o) => o.value).join(" / ")}
                    </span>
                    <span className="flex shrink-0 items-center gap-2 text-muted-foreground">
                      {variant.price &&
                        formatPrice(
                          variant.price.price,
                          variant.price.currency
                        )}
                      {variant.available === false && (
                        <Badge variant="outline">Out of stock</Badge>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

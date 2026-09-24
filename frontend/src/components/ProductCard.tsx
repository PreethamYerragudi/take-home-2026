import { Link } from "react-router-dom"

import { AspectRatio } from "@/components/ui/aspect-ratio"
import { Card, CardContent } from "@/components/ui/card"
import { formatPrice } from "@/lib/format"
import { productImageTransitionName } from "@/lib/utils"
import type { ProductSummary } from "@/types"

export function ProductCard({ product }: { product: ProductSummary }) {
  const onSale =
    product.price.compare_at_price != null &&
    product.price.compare_at_price > product.price.price

  return (
    <Link
      to={`/product/${product.slug}`}
      className="group relative z-0 block hover:z-10"
      viewTransition
    >
      <Card className="h-full gap-3 overflow-hidden transition-transform duration-300 ease-out will-change-transform hover:scale-105 hover:-translate-y-1.5 hover:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.35)]">
        <AspectRatio ratio={1} className="bg-muted">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="absolute inset-0 h-full w-full object-cover"
              style={{
                viewTransitionName: productImageTransitionName(product.slug),
              }}
              loading="lazy"
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-xs text-muted-foreground">
              No image
            </div>
          )}
        </AspectRatio>
        <CardContent className="space-y-1">
          <p className="text-xs tracking-wide text-muted-foreground uppercase">
            {product.brand}
          </p>
          <h3 className="line-clamp-2 text-sm leading-snug font-medium">
            {product.name}
          </h3>
          <div className="flex items-baseline gap-2 pt-1">
            <span className="text-sm font-semibold">
              {formatPrice(product.price.price, product.price.currency)}
            </span>
            {onSale && (
              <span className="text-xs text-muted-foreground line-through">
                {formatPrice(
                  product.price.compare_at_price as number,
                  product.price.currency
                )}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}

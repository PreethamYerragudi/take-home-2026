export { cn } from "cn"

export function productImageTransitionName(slug: string) {
  return `product-image-${slug.replace(/[^a-zA-Z0-9_-]/g, "-")}`
}

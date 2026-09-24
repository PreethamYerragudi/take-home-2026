export interface Price {
  price: number
  currency: string
  compare_at_price: number | null
}

export interface VariantOption {
  name: string
  value: string
}

export interface Variant {
  options: VariantOption[]
  sku: string | null
  price: Price | null
  available: boolean | null
  image_url: string | null
  url: string | null
}

export interface Category {
  name: string
}

export interface Product {
  name: string
  price: Price
  description: string
  key_features: string[]
  image_urls: string[]
  video_url: string | null
  category: Category
  brand: string
  colors: string[]
  variants: Variant[]
}

export interface ProductSummary {
  slug: string
  name: string
  brand: string
  price: Price
  image_url: string | null
  category: string
}

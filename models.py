from pathlib import Path
from pydantic import BaseModel, field_validator

# Load categories once at module level
CATEGORIES_FILE = Path(__file__).parent / "categories.txt"
VALID_CATEGORIES = set()
if CATEGORIES_FILE.exists():
    with open(CATEGORIES_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                VALID_CATEGORIES.add(line)

class Category(BaseModel):
    # A category from Google's Product Taxonomy
    # https://www.google.com/basepages/producttype/taxonomy.en-US.txt
    name: str

    @field_validator("name")
    @classmethod
    def validate_name_exists(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Category '{v}' is not a valid category in categories.txt")
        return v

class Price(BaseModel):
    price: float
    currency: str
    # If a product is on sale, this is the original price
    compare_at_price: float | None = None

class VariantOption(BaseModel):
    # A single attribute/value pair distinguishing this variant, e.g.
    # ("Color", "Red") or ("Size", "XL"). Attribute names are whatever the
    # source page itself uses, since sites vary attributes they sell by
    # (size, color, fit, material, pack size, etc.)
    name: str
    value: str

class Variant(BaseModel):
    # A single purchasable configuration of the product.
    options: list[VariantOption]
    sku: str | None = None
    price: Price | None = None  # only if this variant is priced differently from the base product
    available: bool | None = None
    image_url: str | None = None
    url: str | None = None

# This is the final product schema that you need to output.
# You may add additional models as needed.
class Product(BaseModel):
    name: str
    price: Price
    description: str
    key_features: list[str]
    image_urls: list[str]
    video_url: str | None = None
    category: Category
    brand: str
    colors: list[str]
    variants: list[Variant]
import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import Price, Product

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"

app = FastAPI(title="Product Catalog API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductSummary(BaseModel):
    slug: str
    name: str
    brand: str
    price: Price
    image_url: str | None = None
    category: str


def _load_products() -> dict[str, Product]:
    products: dict[str, Product] = {}
    for path in sorted(OUTPUT_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            products[path.stem] = Product.model_validate(data)
        except Exception:
            logger.exception(f"Failed to load product from {path.name}")
    return products


_PRODUCTS = _load_products()


@app.get("/api/products")
def list_products() -> list[ProductSummary]:
    return [
        ProductSummary(
            slug=slug,
            name=product.name,
            brand=product.brand,
            price=product.price,
            image_url=product.image_urls[0] if product.image_urls else None,
            category=product.category.name,
        )
        for slug, product in _PRODUCTS.items()
    ]


@app.get("/api/products/{slug}")
def get_product(slug: str) -> Product:
    product = _PRODUCTS.get(slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

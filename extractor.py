"""
LLM-based extraction of a `Product` from a preprocessed product page.

Two-stage design:
  1. One structured-output call extracts everything except the taxonomy
     category: name, price, description, features, images, brand, colors,
     variants -- plus a short free-text category guess used only to seed
     step 2.
  2. Category resolution walks Google's Product Taxonomy tree one level at a
     time, asking a cheap model to pick among that level's children (or stop
     at the current node), with the choice constrained to a dynamic
     `Literal[...]` of just that level's valid values. Every prefix of every
     taxonomy entry is itself a valid category (verified against
     categories.txt), so the final joined path always passes `Category`'s
     validator -- no retry/repair loop is needed, and the model can never
     land on an invalid category.

Both stages key off generic signals (structured data, meta tags, page text,
a fixed external taxonomy file) rather than any specific site's markup.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, create_model

import ai
from models import Category, Price, Product, VALID_CATEGORIES, Variant
from preprocessor import preprocess_html

EXTRACTION_MODEL = "openai/gpt-5-mini"
CATEGORY_MODEL = "openai/gpt-5-nano"

_STOP = "<STOP: current category is precise enough>"

EXTRACTION_SYSTEM_PROMPT = """\
You extract structured product data from an e-commerce product detail page.

You are given signals mechanically pulled from the page's raw HTML: any \
schema.org/ld+json data, any embedded application state, meta tags, a list \
of candidate image URLs found on the page, and the visible page text. Use \
ONLY this information -- never invent values that aren't present. If a \
field genuinely isn't present on the page, use an empty value.

Guidance:
- key_features: the product's bullet-point features/specs as shown on the \
page, not ad copy.
- image_urls: from the candidate list, return only URLs that are actual \
photos of this product (exclude site logos, nav icons, unrelated \
banners/promo art). Many candidates are the same photo at different \
resolutions (filenames or query params differing only by size/width/height) \
-- collapse each distinct photo down to its single highest-resolution URL.
- colors: every color option offered for the product, if it comes in more \
than one.
- variants: every purchasable configuration (e.g. one per SKU) listed in the \
page's data. If the product varies along more than one attribute (e.g. both \
color AND size) and you can confidently determine the full combination for \
a variant, include all of those attributes together in its `options` (one \
options entry per attribute) rather than just one dimension. But do not let \
uncertainty about a second attribute cause you to omit variants entirely -- \
if you can only confidently determine one dimension (e.g. the list of \
colors, without a reliable per-color size breakdown), still return one \
variant per value of that dimension. Returning partial variant data is \
always better than returning none. Use the attribute names the page itself \
uses.
- category_guess: a short free-text description of what kind of product \
this is (a few words). It will be matched against a fixed taxonomy \
afterward, so it does not need to be exact.
"""


class ProductDraft(BaseModel):
    name: str
    price: Price
    description: str
    key_features: list[str]
    image_urls: list[str]
    video_url: str | None = None
    brand: str
    colors: list[str]
    variants: list[Variant]
    category_guess: str


async def extract_product(
    html: str,
    extraction_model: str = EXTRACTION_MODEL,
    category_model: str = CATEGORY_MODEL,
) -> Product:
    page = preprocess_html(html)
    document = page.to_llm_document()

    draft = await ai.responses(
        extraction_model,
        [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": document},
        ],
        text_format=ProductDraft,
    )

    category = await _resolve_category(draft, category_model)

    return Product(
        name=draft.name,
        price=draft.price,
        description=draft.description,
        key_features=draft.key_features,
        image_urls=draft.image_urls,
        video_url=draft.video_url,
        category=category,
        brand=draft.brand,
        colors=draft.colors,
        variants=draft.variants,
    )


def _build_taxonomy_tree() -> dict:
    tree: dict = {}
    for cat in VALID_CATEGORIES:
        node = tree
        for part in cat.split(" > "):
            node = node.setdefault(part, {})
    return tree


_TAXONOMY_TREE = _build_taxonomy_tree()


async def _resolve_category(draft: ProductDraft, model: str) -> Category:
    context = (
        f"Product name: {draft.name}\n"
        f"Brand: {draft.brand}\n"
        f"Category guess: {draft.category_guess}\n"
        f"Description: {draft.description}"
    )

    path: list[str] = []
    node = _TAXONOMY_TREE
    while node:
        children = sorted(node.keys())
        choices = children if not path else [_STOP, *children]

        StepChoice = create_model("CategoryStep", choice=(Literal[tuple(choices)], ...))

        instructions = "Pick the single best-matching category from the allowed choices below."
        if path:
            instructions += f" If the current category path is already precise enough, pick {_STOP!r} instead of descending further."

        result = await ai.responses(
            model,
            [
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": (
                        f"{context}\n\n"
                        f"Current category path: {' > '.join(path) or '(none yet)'}\n\n"
                        "Allowed choices:\n" + "\n".join(choices)
                    ),
                },
            ],
            text_format=StepChoice,
        )

        if result.choice == _STOP:
            break
        path.append(result.choice)
        node = node[result.choice]

    return Category(name=" > ".join(path))


if __name__ == "__main__":
    import asyncio
    import logging
    import sys

    logging.basicConfig(level=logging.INFO)

    path_arg = sys.argv[1] if len(sys.argv) > 1 else "data/nike.html"
    with open(path_arg, encoding="utf-8") as f:
        html_content = f.read()

    product = asyncio.run(extract_product(html_content))
    print(product.model_dump_json(indent=2))

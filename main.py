import asyncio
import logging
from pathlib import Path

from extractor import extract_product

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"

logger = logging.getLogger(__name__)


async def process_file(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    logger.info(f"Extracting product from {path.name}")
    product = await extract_product(html)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{path.stem}.json"
    out_path.write_text(product.model_dump_json(indent=2))
    logger.info(f"{path.name} -> {out_path}")


async def main() -> None:
    html_files = sorted(DATA_DIR.glob("*.html"))
    results = await asyncio.gather(
        *(process_file(p) for p in html_files), return_exceptions=True
    )

    failures = [(p, r) for p, r in zip(html_files, results) if isinstance(r, Exception)]
    for path, error in failures:
        logger.error(f"Failed to extract {path.name}: {error}")

    logger.info(f"Done: {len(html_files) - len(failures)}/{len(html_files)} succeeded")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

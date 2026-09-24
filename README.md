## Channel3 Take Home Assignment

System Design answers at the bottom

### Prerequisites

- Python 3.12 (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) (recommended) or plain `pip` + `venv`
- Node.js 18+ and npm
- An [OpenRouter](https://openrouter.ai/) API key, only needed if you want to
  re-run the extraction pipeline yourself (the repo already ships with
  pre-extracted data in `output/`, so this is optional for just running the
  site)

### 1. Set up the environment file

Copy your OpenRouter key into `.env` at the repo root:

```
OPEN_ROUTER_API_KEY=sk-or-...
```

This is only read by `ai.py` when the extraction pipeline actually calls out
to a model. The backend and frontend don't need it just to serve the
already-extracted products in `output/`.

### 2. Install backend dependencies

With `uv`:

```bash
uv sync
```

Without `uv` (plain venv):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
```

### 4. Run the backend API

From the repo root:

```bash
uv run uvicorn server:app --reload --port 8000
# or, without uv:
uvicorn server:app --reload --port 8000
```

This loads every `output/*.json` file into memory and serves:

- `GET /api/products` — list of all products (summary view)
- `GET /api/products/{slug}` — full detail for one product

Leave this running in its own terminal.

### 5. Run the frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Vite will print a local URL (usually `http://localhost:5173`). Open it in a
browser to see the catalog. The dev server proxies any `/api/*` request to
`http://127.0.0.1:8000`, so the backend from step 4 needs to already be
running.

### (Optional) Re-running the extraction pipeline

The `output/` directory is already populated, so you don't need to do this
to browse the site. It's only relevant if you're adding a new product or
want to regenerate the existing ones.

Test extraction on a single page without writing anything:

```bash
python extractor.py data/nike.html
```

Regenerate `output/*.json` for every file in `data/`:

```bash
python main.py
```

`main.py` reprocesses **every** `*.html` file in `data/` each time it runs,
so it will overwrite all existing products, not just new ones. Each product
costs real LLM API calls, so re-running this against a large `data/`
directory isn't free.

To add a brand-new product:

1. Fetch the raw page: `curl -o data/newproduct.html "https://example.com/product/123"`
   (some sites block plain `curl` with bot detection; this works best on
   straightforward server-rendered pages).
2. Sanity-check it in isolation: `python extractor.py data/newproduct.html`
3. Run the full batch to write it into `output/`: `python main.py`
4. Restart the backend (step 4 above) so it picks up the new file — it only
   loads `output/` once, at startup.

### Building the frontend for production

```bash
cd frontend
npm run build
```

Output goes to `frontend/dist/`.

### Troubleshooting

- **CORS errors in the browser console**: `server.py` only allows requests
  from `http://localhost:5173` and `http://127.0.0.1:5173`. If port 5173 is
  already taken, Vite will silently pick 5174, 5175, etc., and the backend
  will reject those origins. Either free up 5173 first, or add the actual
  port Vite printed to the `allow_origins` list in `server.py`.
- **`ValueError: OPEN_ROUTER_API_KEY not found in environment`**: you're
  trying to run the extraction pipeline (`main.py` / `extractor.py`)
  without a key set in `.env`. Not needed for just running the backend/frontend.
- **`address already in use` on port 8000**: something (maybe a previous
  `uvicorn` run) is still bound to that port. Find it with
  `lsof -nP -iTCP:8000 -sTCP:LISTEN` and kill it, or run on a different port.

Happy coding!

### System Design Answers
The pipeline works great for five products and would fall over almost immediately at fifty million. Right now the whole thing loads every JSON file into memory when the server starts and reprocesses a fixed folder of HTML files in one big batch call, so the first thing to go is storage: the catalog needs to live in an actual database with a search index next to it, not a directory of files a Python dict slurps up on boot. The API needs to get paginated and stateless so you can just run more copies of it, and ingestion needs to turn into a real queue with retries, instead of one script that assumes every product fits in one run. The part of this system I'd actually keep is the instinct behind it: pull structured signals off the page (the schema.org data, the embedded app state) instead of hand writing a scraper for every retailer, and force the model's output into a shape that can't be wrong, like the taxonomy walk does. What won't survive is how much of the work is currently just "ask the LLM." Running a big model over the full text of every page, plus another model call for every level of the category tree, is totally fine for five products and would get expensive and slow fast at scale. Most of that should be handled by cheap heuristics or a classifier, saving the LLM for the pages that genuinely don't have any structured data to lean on, and none of it works long term without some way to keep prices and stock levels fresh instead of treating a scrape as the truth forever.

On the frontend side, if I were building this for agents rather than people clicking around, I'd want the API to feel like a set of tools an agent can call directly instead of a pile of JSON it has to guess at. That means real search (something that understands "a cooling mattress topper under $200" instead of just matching keywords), decent filtering, and a way to pull a handful of products at once so an agent isn't reconstructing a comparison table by hand. Given where this is running, I'd honestly just ship it as an MCP server alongside a normal REST API, so something like Claude can browse the catalog as a native tool rather than someone building a custom integration for every agent platform. The bigger unlock, though, is treating checkout as part of the API instead of an afterthought: some kind of scoped purchase token so an agent can actually buy something on a user's behalf with clear limits and a receipt, because that's really the line between an API that shows you products and one that lets an agent shop. Past that, the stuff that actually helps other developers build on this is pretty unglamorous: a proper SDK instead of raw fetch calls, webhooks for price drops and restocks so people aren't polling, a sandbox catalog to build against, and just handing over the UI pieces we already built here, since nobody should have to rediscover the same image aspect ratio bug we just fixed.

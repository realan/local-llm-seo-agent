# Context Dump

## Current State

- Project: `local-llm-seo-agent`
- Date of snapshot: 2026-04-17
- Runtime status:
  - Stage 01: implemented
  - Stage 02: implemented
  - Stage 03: implemented
  - Stages 04-05: specifications exist in `_docs`, but no separate new runtime stages beyond the current Stage 03 implementation

## Implemented Functionality

### CLI

File: `app/main.py`

Available commands:

- `python -m app.main health`
- `python -m app.main demo`
- `python -m app.main demo --scenario calculator|file_read|http_get`
- `python -m app.main demo --task "..."`
- `python -m app.main chat`
- `python -m app.main process-catalog --input ... --sheet ... --limit ...`

Notes:

- CLI uses `click`, not `typer`
- `chat` is interactive, but stateless between user turns
- `process-catalog` is connected to the real pipeline, not a stub

### Agent Loop

Files:

- `app/agent/runner.py`
- `app/agent/prompts.py`
- `app/agent/schemas.py`

Implemented:

- thought -> action -> observation loop
- strict JSON output parsing
- one repair attempt on invalid JSON
- step history collection
- max step enforcement
- formatted console output

Max steps actually used:

- `demo_mode`: 5
- other modes: 8

### Demo / Chat Tools

Files:

- `app/tools/calculator.py`
- `app/tools/file_tools.py`
- `app/tools/http_fetch.py`
- `app/tools/excel_tools.py`

Registered in `demo` and `chat`:

- `calculator`
- `read_text_file`
- `http_get`
- `get_excel_info`
- `read_excel_row`

Important behavior:

- plain text files should go through `read_text_file`
- `.xlsx` files should go through Excel tools
- the prompt now explicitly tells the model not to use `read_text_file` for Excel

### Catalog Pipeline

Files:

- `app/services/catalog_processor.py`
- `app/services/symbolism_service.py`
- `app/tools/catalog_tools.py`
- `app/tools/excel_tools.py`

Implemented pipeline:

1. copy input workbook to output workbook
2. normalize headers
3. ensure output columns exist
4. read each row
5. detect entity type from YAML dictionary
6. classify size from title hints, weight, height
7. load symbolism from cache or fetch through HTTP lookup
8. generate SEO fields through LLM with structured JSON validation
9. write row-level result fields

Row statuses currently used:

- `success`
- `skipped`
- `needs_review`
- `error`

Catalog output fields currently written:

- `entity_type`
- `entity_confidence`
- `size_tag`
- `size_reason`
- `symbolism_summary`
- `symbolism_source_note`
- `seo_keywords`
- `seo_title`
- `seo_description`
- `product_description`
- `processed_status`
- `processed_error`

### Runtime Data

Files now present in runtime:

- `app/data/entity_dictionary.yaml`
- `app/data/size_rules.yaml`
- `app/cache/symbolism_cache.json`

These files are now actually used by code.

## Repo Structure

Key runtime files:

- `app/main.py`
- `app/agent/prompts.py`
- `app/agent/runner.py`
- `app/agent/schemas.py`
- `app/llm/ollama_client.py`
- `app/tools/base.py`
- `app/tools/calculator.py`
- `app/tools/file_tools.py`
- `app/tools/http_fetch.py`
- `app/tools/excel_tools.py`
- `app/tools/catalog_tools.py`
- `app/services/catalog_processor.py`
- `app/services/symbolism_service.py`
- `app/data/entity_dictionary.yaml`
- `app/data/size_rules.yaml`
- `app/cache/symbolism_cache.json`
- `samples/test.txt`
- `samples/products.xlsx`

Tests:

- `tests/test_demo.py`
- `tests/test_cli.py`
- `tests/test_catalog.py`
- `tests/conftest.py`

## Ollama / Config

File: `app/llm/ollama_client.py`

Current behavior:

- loads `.env` via `python-dotenv`
- supports environment-based config
- checks both Ollama reachability and installed model availability
- handles missing model with explicit error instead of uncaught retry stack

Supported environment variables:

- `OLLAMA_MODEL`
- `OLLAMA_ENDPOINT`
- `OLLAMA_TIMEOUT_SEC`
- `SYMBOLISM_LOOKUP_URL_TEMPLATE`

Template file:

- `.env.example`

## Dependencies

Current relevant dependencies in `requirements.txt`:

- `requests`
- `pandas`
- `openpyxl`
- `pydantic`
- `click`
- `rich`
- `tenacity`
- `orjson`
- `python-dotenv`
- `PyYAML`
- `pytest`
- `pytest-cov`

## Tests / Verification

Current automated coverage in repo:

- CLI command parsing
- chat command loop behavior
- demo tools
- agent runner initialization and failure handling
- catalog helpers
- catalog workbook pipeline on temporary `.xlsx`

Most recent known local result during implementation:

- `19 passed, 2 skipped`

Skipped tests:

- integration tests that require a live Ollama instance

## Known Gaps / Risks

- `chat` is not conversational memory; each request is isolated
- demo/chat Excel handling depends on the model selecting the correct tool arguments
- `read_text_file` still allows absolute paths and has no strict confinement
- calculator fallback still uses restricted `eval` when `numexpr` is unavailable
- `CatalogProcessor` uses its own structured LLM prompt and validation, not the full agent loop
- `SymbolismService` currently performs a simple HTTP lookup trigger and then builds summary from dictionary defaults; external lookup is lightweight, not semantically rich
- warnings remain from upstream dependencies:
  - Pydantic V2 deprecation around class-based config in existing schema models
  - openpyxl deprecation warnings about `datetime.utcnow()`

## Current Practical Usage

For one-off demo tasks:

```bash
python -m app.main demo --task "Calculate (345 + 55) * 3"
```

For interactive stateless mode:

```bash
python -m app.main chat
```

For catalog processing:

```bash
python -m app.main process-catalog --input samples/products.xlsx --sheet products
```

For health check:

```bash
python -m app.main health
```

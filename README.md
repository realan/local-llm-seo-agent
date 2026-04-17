# Local LLM SEO Agent

Local Python agent over Ollama for two tasks:

- demo/homework scenarios with a thought -> action -> observation loop
- Excel catalog enrichment with SEO fields written into a new workbook

Default model is `qwen3.5:4b`, but the runtime can be reconfigured through environment variables.

## Status

Current codebase state:

- Stage 01: implemented
- Stage 02: implemented
- Stage 03: implemented
- Interactive `chat` mode: implemented
- Catalog pipeline: implemented

## Requirements

- Python 3.11+
- Ollama running locally
- A locally installed Ollama model, for example `qwen3.5:4b` or `qwen3:0.6b`

## Setup

### 1. Install Ollama and a model

```bash
ollama pull qwen3.5:4b
ollama serve
```

If you already use another local model, configure it in `.env`.

### 2. Install Python dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Example:

```bash
OLLAMA_MODEL=qwen3:0.6b
OLLAMA_ENDPOINT=http://localhost:11434/api/generate
OLLAMA_TIMEOUT_SEC=120
SYMBOLISM_LOOKUP_URL_TEMPLATE=https://httpbin.org/anything/symbolism?query={query}
```

### 4. Verify setup

```bash
python -m app.main health
```

If the configured model is missing, the command will show available installed models.

## Commands

### Health

```bash
python -m app.main health
```

### Demo Mode

Run all predefined scenarios:

```bash
python -m app.main demo
```

Run one scenario:

```bash
python -m app.main demo --scenario calculator
python -m app.main demo --scenario file_read
python -m app.main demo --scenario http_get
```

Run a custom one-shot task:

```bash
python -m app.main demo --task "Calculate (345 + 55) * 3"
```

### Chat Mode

Interactive stateless mode:

```bash
python -m app.main chat
```

Example:

```text
You > Calculate (12 + 8) * 4
You > Read samples/test.txt and count the lines
You > Open samples/products.xlsx, sheet products, and tell me how many data rows it has
You > exit
```

Notes:

- each message is processed as a separate task
- there is no memory between turns
- for Excel files, use `samples/products.xlsx` and specify the sheet, usually `products`

### Catalog Mode

Run the catalog pipeline:

```bash
python -m app.main process-catalog --input samples/products.xlsx --sheet products
```

Example with custom output path:

```bash
python -m app.main process-catalog \
  --input samples/products.xlsx \
  --output results/products_result.xlsx \
  --sheet products \
  --limit 5
```

What `process-catalog` does:

- copies input workbook to a new output workbook
- normalizes column headers
- adds missing output columns
- detects entity type from YAML dictionary
- classifies size from title hints, weight, and height
- loads/fetches symbolism and caches by entity type
- asks the LLM for structured SEO output
- writes row-level result fields

## Sample Files

Included in the repo:

- `samples/test.txt`
- `samples/products.xlsx`

## Project Structure

```text
app/
  main.py
  agent/
    prompts.py
    runner.py
    schemas.py
  llm/
    ollama_client.py
  tools/
    base.py
    calculator.py
    file_tools.py
    http_fetch.py
    excel_tools.py
    catalog_tools.py
  services/
    catalog_processor.py
    symbolism_service.py
  data/
    entity_dictionary.yaml
    size_rules.yaml
  cache/
    symbolism_cache.json

samples/
tests/
```

## Implemented Tools

Demo / chat tools:

- `calculator`
- `read_text_file`
- `http_get`
- `get_excel_info`
- `read_excel_row`

Catalog helpers:

- entity detection from YAML aliases
- size classification
- base tag generation
- symbolism cache load/save
- workbook read/write helpers

## Catalog Output Fields

The pipeline writes:

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

## Current Technical Notes

- CLI is implemented with `click`
- `.env` is loaded through `python-dotenv`
- YAML runtime config is loaded through `PyYAML`
- invalid JSON from the model gets one repair attempt
- input workbook is preserved; results go to a new file
- row-level catalog failures do not stop the whole run

## Tests

Main tests:

- `tests/test_demo.py`
- `tests/test_cli.py`
- `tests/test_catalog.py`

Typical run:

```bash
pytest tests/test_cli.py tests/test_demo.py tests/test_catalog.py -q
```

Current known result during latest update:

- `19 passed, 2 skipped`

## Known Limitations

- `chat` mode is not a real conversational assistant with memory
- Excel questions in `chat` still depend on the model choosing the right tool arguments
- `read_text_file` is permissive with absolute paths
- calculator fallback uses restricted `eval` if `numexpr` is unavailable
- symbolism HTTP lookup is lightweight; summary content still mainly comes from dictionary defaults

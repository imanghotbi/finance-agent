# Finance Agent

Finance Agent is a headless multi-agent stock analysis pipeline for Iranian market symbols.
It collects market/fundamental/social/news data, runs a LangGraph workflow, and stores final reports in MongoDB.

## What It Does

Given symbols like `فملی` or `فولاد`, the app:

1. refreshes or reuses cached symbol data
2. runs technical, fundamental, and social/news analysis subgraphs in parallel
3. generates consensus reports
4. creates a final investment memo
5. records runtime per symbol in a CSV file
6. supports resume after crash using a checkpoint file

## Architecture

Main workflow nodes:

- `data_preparation`
- `technical_graph`
- `fundamental_graph`
- `social_news_graph`
- `reporter_agent`

Key entrypoints:

- [`main.py`](/Users/mac/Desktop/finance_agent/main.py): batch runner (CLI)
- [`src/workflow/graph_builder.py`](/Users/mac/Desktop/finance_agent/src/workflow/graph_builder.py): graph construction
- [`src/services/prepare_data.py`](/Users/mac/Desktop/finance_agent/src/services/prepare_data.py): data fetch + preprocessing

## Configuration

Settings are loaded from `.env` (see [`src/core/config.py`](/Users/mac/Desktop/finance_agent/src/core/config.py)).

Minimum required values:

```env
MONGO_ENDPOINT=localhost:27017
MONGO_DB_NAME=finance_agent

RAPID_API_KEY=your_rapid_api_key
PROXY_URL=http://your-proxy-if-needed

MODEL_API_KEY=your_model_api_key
MODEL_BASE_URL=https://api.openai.com/v1
MODEL_NAME=qwen/qwen3-235b-a22b
MODEL_REASONING_EFFORT=low
```

## Install

```bash
pip install -r requirements.txt
```

## Run Batch Flow

Create a symbol file (one symbol per line):

```text
فملی
فولاد
# lines starting with # are ignored
```

Run:

```bash
python main.py \
  --symbols-file symbols.txt \
  --runtime-file runtime_report.csv \
  --checkpoint-file .files/batch_checkpoint.json
```

Optional:

```bash
python main.py --stop-on-error
```

CLI options:

- `--symbols-file`: input text file (default: `symbols.txt`)
- `--runtime-file`: CSV output for runtime/status rows (default: `runtime_report.csv`)
- `--checkpoint-file`: JSON state file for resume support (default: `.files/batch_checkpoint.json`)
- `--stop-on-error`: stop immediately when one symbol fails

## Crash Recovery

The batch runner writes progress into `--checkpoint-file` after each symbol and before each run starts.
If the process crashes, rerun the same command:

- symbols already marked as completed are skipped
- unfinished symbols are processed
- runtime rows are appended to `--runtime-file`

Current resume scope:

- resume is at **symbol level** (not node-level within a symbol)
- if a crash happens during one symbol, that symbol is re-run on next execution

## Output Files

- Runtime CSV (`--runtime-file`): per-symbol status and runtime
- Checkpoint JSON (`--checkpoint-file`): completed/failed/in-progress symbols

Runtime CSV columns:

- `symbol`
- `status` (`success` or `failed`)
- `runtime_seconds`
- `started_at`
- `finished_at`
- `session_id`
- `error`

Checkpoint shape:

```json
{
  "created_at": "2026-04-13T07:00:00+00:00",
  "updated_at": "2026-04-13T07:12:21+00:00",
  "completed": {
    "فملی": {
      "symbol": "فملی",
      "status": "success"
    }
  },
  "failed": {},
  "in_progress": null
}
```

## Persistence

MongoDB stores:

- cached analysis payloads
- per-node LLM usage metadata
- final agent run state and report

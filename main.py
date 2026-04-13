import argparse
import asyncio
import csv
import json
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_GRAPH_APP = None
_APP_LOGGER = None


def get_runtime_components():
    global _GRAPH_APP, _APP_LOGGER
    if _GRAPH_APP is None or _APP_LOGGER is None:
        from src.workflow.graph_builder import app as graph_app
        from src.core.logger import logger

        _GRAPH_APP = graph_app
        _APP_LOGGER = logger
    return _GRAPH_APP, _APP_LOGGER


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run batch stock analysis for symbols from a file.")
    parser.add_argument(
        "--symbols-file",
        default="symbols.txt",
        help="Path to a text file containing one symbol per line.",
    )
    parser.add_argument(
        "--runtime-file",
        default="runtime_report.csv",
        help="CSV output file containing per-symbol runtime.",
    )
    parser.add_argument(
        "--checkpoint-file",
        default=".files/batch_checkpoint.json",
        help="JSON checkpoint file used to resume after crash.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the run immediately when one symbol fails.",
    )
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_symbols(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Symbols file not found: {path}")

    symbols: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        symbols.append(line)

    unique_symbols = list(dict.fromkeys(symbols))
    if not unique_symbols:
        raise ValueError(f"No valid symbols found in: {path}")

    return unique_symbols


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "completed": {},
            "failed": {},
            "in_progress": None,
        }

    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("completed", {})
    data.setdefault("failed", {})
    data.setdefault("in_progress", None)
    return data


def append_runtime_row(runtime_file: Path, row: dict[str, Any]) -> None:
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "symbol",
        "status",
        "runtime_seconds",
        "started_at",
        "finished_at",
        "session_id",
        "error",
    ]

    write_header = not runtime_file.exists() or runtime_file.stat().st_size == 0
    with runtime_file.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


async def run_symbol(symbol: str, session_id: str) -> dict[str, Any]:
    graph_app, _ = get_runtime_components()
    started_at = utc_now_iso()
    started_monotonic = time.perf_counter()

    inputs = {
        "symbol": symbol,
        "analysis_started_at": started_at,
    }
    config = {
        "configurable": {
            "thread_id": session_id,
            "session_id": session_id,
        }
    }

    final_state = await graph_app.ainvoke(inputs, config)

    measured_runtime = round(time.perf_counter() - started_monotonic, 2)
    finished_at = utc_now_iso()

    return {
        "state": final_state,
        "started_at": started_at,
        "finished_at": finished_at,
        "runtime_seconds": final_state.get("time_consumption_seconds") or measured_runtime,
    }


async def run_batch(args: argparse.Namespace) -> int:
    _, logger = get_runtime_components()
    symbols_file = Path(args.symbols_file)
    runtime_file = Path(args.runtime_file)
    checkpoint_file = Path(args.checkpoint_file)

    symbols = read_symbols(symbols_file)
    checkpoint = load_checkpoint(checkpoint_file)

    completed: dict[str, Any] = checkpoint["completed"]
    failed: dict[str, Any] = checkpoint["failed"]

    for index, symbol in enumerate(symbols, start=1):
        if symbol in completed:
            logger.info("[%s/%s] Skipping already completed symbol: %s", index, len(symbols), symbol)
            continue

        session_id = f"{symbol}-{uuid.uuid4()}"
        checkpoint["in_progress"] = {
            "symbol": symbol,
            "session_id": session_id,
            "started_at": utc_now_iso(),
        }
        checkpoint["updated_at"] = utc_now_iso()
        atomic_write_json(checkpoint_file, checkpoint)

        logger.info("[%s/%s] Running analysis for symbol: %s", index, len(symbols), symbol)

        try:
            result = await run_symbol(symbol=symbol, session_id=session_id)
            row = {
                "symbol": symbol,
                "status": "success",
                "runtime_seconds": result["runtime_seconds"],
                "started_at": result["started_at"],
                "finished_at": result["finished_at"],
                "session_id": session_id,
                "error": "",
            }
            append_runtime_row(runtime_file, row)

            completed[symbol] = {
                **row,
                "final_report_preview": str(result["state"].get("final_report", ""))[:240],
            }
            failed.pop(symbol, None)
            logger.info("Completed symbol: %s (runtime=%ss)", symbol, result["runtime_seconds"])

        except Exception as exc:
            finished_at = utc_now_iso()
            row = {
                "symbol": symbol,
                "status": "failed",
                "runtime_seconds": "",
                "started_at": checkpoint["in_progress"]["started_at"],
                "finished_at": finished_at,
                "session_id": session_id,
                "error": str(exc),
            }
            append_runtime_row(runtime_file, row)

            failed[symbol] = row
            logger.exception("Analysis failed for symbol: %s", symbol)

            if args.stop_on_error:
                checkpoint["updated_at"] = utc_now_iso()
                atomic_write_json(checkpoint_file, checkpoint)
                raise

        finally:
            checkpoint["in_progress"] = None
            checkpoint["updated_at"] = utc_now_iso()
            atomic_write_json(checkpoint_file, checkpoint)

    logger.info(
        "Batch run finished. completed=%s failed=%s total=%s runtime_file=%s checkpoint=%s",
        len(completed),
        len(failed),
        len(symbols),
        runtime_file,
        checkpoint_file,
    )
    return 0 if not failed else 1


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run_batch(args))
    except KeyboardInterrupt:
        _, logger = get_runtime_components()
        logger.warning("Execution interrupted by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

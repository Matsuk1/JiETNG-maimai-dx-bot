#!/usr/bin/env python3
"""Compare CPU OCR configurations in isolated processes, without Codex calls."""
import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run_worker(args):
    sys.path.insert(0, str(ROOT))
    import psutil
    from modules.score_recognition.recognizer import (
        recognize_score_image_bytes, validate_recognized_judgement,
    )
    from modules.score_recognition.ocr import OCR_FIELDS

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    results = []
    process = psutil.Process()
    for iteration in range(args.runs):
        for path in args.images:
            started = time.perf_counter()
            row = {"image": str(path), "iteration": iteration + 1}
            try:
                # Explicit fields disables the exception-path Codex fallback.
                result = recognize_score_image_bytes(Path(path).read_bytes(), fields=OCR_FIELDS)
                validation_started = time.perf_counter()
                # No image bytes: validation cannot invoke Codex either.
                result = validate_recognized_judgement(result, ver=args.version)
                row.update(timing=result.get("timing"), parsed=result.get("parsed"),
                           validation=result.get("validation"),
                           validation_seconds=time.perf_counter() - validation_started)
            except Exception as exc:
                logging.exception("Benchmark image failed")
                row["error"] = str(exc)
            row["seconds"] = time.perf_counter() - started
            try:
                row["rss_mb"] = round(process.memory_info().rss / 1024**2, 1)
                child_rss = 0
                for child in process.children(recursive=True):
                    try:
                        child_rss += child.memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
                row["children_rss_mb"] = round(child_rss / 1024**2, 1)
            except (psutil.Error, OSError) as exc:
                row["memory_measurement_error"] = str(exc)
            results.append(row)
            Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--version", choices=("jp", "cn"), default="jp")
    parser.add_argument("--output", type=Path, default=Path("ocr-benchmark"))
    parser.add_argument("--timeout", type=int, default=1800, help="Seconds per configuration")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.runs < 1 or args.timeout < 1:
        parser.error("runs and timeout must be positive")
    args.images = [path.resolve(strict=True) for path in args.images]
    if args.worker:
        run_worker(args)
        return
    args.output.mkdir(parents=True, exist_ok=True)
    summary = []
    for enabled in (0, 1):
        for threads in (4, 8):
            name = f"onednn-{enabled}-threads-{threads}"
            env = os.environ.copy()
            for key in ("JIETNG_OCR_CPU_THREADS", "JIETNG_TABLE_OCR_CPU_THREADS",
                        "PADDLE_PDX_CPU_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
                env[key] = str(threads)
            for key in ("JIETNG_OCR_ENABLE_MKLDNN", "JIETNG_TABLE_OCR_ENABLE_MKLDNN"):
                env[key] = str(enabled)
            command = [sys.executable, str(Path(__file__).resolve()), "--worker",
                       "--runs", str(args.runs), "--version", args.version,
                       "--output", str((args.output / f"{name}.json").resolve()),
                       *map(str, args.images)]
            # Remove old results so a startup failure cannot reuse stale measurements.
            (args.output / f"{name}.json").unlink(missing_ok=True)
            print(f"Running {name}", flush=True)
            # Separate process groups let a timeout stop Paddle table workers too.
            with (args.output / f"{name}.log").open("w") as log:
                process = subprocess.Popen(command, env=env, stdout=log, stderr=log,
                                           start_new_session=True)
                try:
                    code = process.wait(timeout=args.timeout)
                except subprocess.TimeoutExpired:
                    import signal
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    code = "timeout"
            entry = {"configuration": name, "exit_code": code}
            result_path = args.output / f"{name}.json"
            if result_path.exists():
                rows = json.loads(result_path.read_text())
                completed = [row for row in rows if "error" not in row]
                warm = [row["seconds"] for row in completed if row["iteration"] > 1]
                entry.update(completed=len(completed), errors=len(rows) - len(completed),
                             warm_median_seconds=statistics.median(warm) if warm else None)
            summary.append(entry)
            print(f"  {entry}", flush=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Results and stage logs: {args.output.resolve()}")


if __name__ == "__main__":
    main()

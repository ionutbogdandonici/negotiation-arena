import csv
from pathlib import Path
from typing import Any


RESULTS_DIR = Path("output")
GLOBAL_RESULTS_PATH = RESULTS_DIR / "global_results.csv"
GLOBAL_RESULT_COLUMNS = [
    "timestamp_utc",
    "run_id",
    "scenario_file",
    "scenario_name",
    "num_agents",
    "agents_model",
    "agents_temperature",
    "round_judge_model",
    "round_judge_temperature",
    "final_judge_model",
    "final_judge_temperature",
    "mode",
    "max_rounds",
    "effective_rounds",
    "allow_partial_agreements",
    "require_unanimous_agreement",
    "agreement_status",
    "conversation_history",
    "utility_total_history",
    "unanimous",
    "final_persuasion",
    "final_deception",
    "final_concession",
    "final_cooperation",
    "final_summary",
    "interaction_pattern",
    "dominant_agent",
]


def append_global_result(row: dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    normalized_row = {}
    for key in GLOBAL_RESULT_COLUMNS:
        value = row.get(key, "")
        normalized_row[key] = "" if value is None else str(value)

    existing_rows: list[dict[str, str]] = []
    should_rewrite = False
    if GLOBAL_RESULTS_PATH.exists():
        with GLOBAL_RESULTS_PATH.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_header = reader.fieldnames or []
            if existing_header != GLOBAL_RESULT_COLUMNS:
                should_rewrite = True
                existing_rows = list(reader)

    if should_rewrite:
        with GLOBAL_RESULTS_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=GLOBAL_RESULT_COLUMNS)
            writer.writeheader()
            for raw_row in existing_rows:
                migrated = {}
                for key in GLOBAL_RESULT_COLUMNS:
                    value = raw_row.get(key, "")
                    migrated[key] = "" if value is None else str(value)
                writer.writerow(migrated)

    file_exists = GLOBAL_RESULTS_PATH.exists()
    with GLOBAL_RESULTS_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=GLOBAL_RESULT_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(normalized_row)


def load_global_results() -> list[dict[str, str]]:
    if not GLOBAL_RESULTS_PATH.exists():
        return []

    with GLOBAL_RESULTS_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        existing_header = reader.fieldnames or []
        raw_rows = list(reader)

    rows = []
    for raw_row in raw_rows:
        normalized = {}
        for key in GLOBAL_RESULT_COLUMNS:
            value = raw_row.get(key, "")
            normalized[key] = "" if value is None else value
        rows.append(normalized)

    if existing_header != GLOBAL_RESULT_COLUMNS:
        with GLOBAL_RESULTS_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=GLOBAL_RESULT_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    return rows

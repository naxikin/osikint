"""Atomic JSON storage (skills.md section 21)."""

import json
import os

from core.logger import get_logger

logger = get_logger("storage")


def save_json(data, output_file: str) -> None:
    temp_file = output_file + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    os.replace(temp_file, output_file)


def load_json(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        logger.warning("failed to load %s: %s", path, exc)
        return None


def save_results(results, output_file: str) -> None:
    save_json(results, output_file)

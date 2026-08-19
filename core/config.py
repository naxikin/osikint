"""Configuration loader: YAML + environment overrides (skills.md section 27)."""

import os
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

from core.exceptions import ConfigurationError

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")

def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


ENV_OVERRIDES = {
    "OSINT_REGION": (("search", "region"), str),
    "OSINT_MAX_RESULTS": (("search", "max_results"), int),
    "OSINT_LEET_VARIANTS": (("search", "leet_variants"), _bool),
    "OSINT_OCR_ENABLED": (("ocr", "enabled"), _bool),
    "OSINT_OUTPUT_DIR": (("output", "directory"), str),
    "OSINT_HEADLESS": (("browser", "headless"), _bool),
    "OSINT_TIMEOUT": (("browser", "timeout"), int),
    "OSINT_PARTIAL_RATIO": (("matching", "partial_ratio_threshold"), int),
    "OSINT_SEQUENCE": (("matching", "sequence_threshold"), int),
    "OSINT_FUZZY": (("matching", "fuzzy_threshold"), int),
    "OSINT_RISK_KEYWORD": (("risk", "keyword_detected"), int),
    "OSINT_RISK_OCR": (("risk", "ocr_detected"), int),
    "OSINT_RISK_REVERSE": (("risk", "reverse_image_match"), int),
    "OSINT_DASHBOARD_AUTH": (("dashboard", "auth", "enabled"), _bool),
}


def _deep_get(data: dict, path: tuple, default=None):
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _deep_set(data: dict, path: tuple, value) -> None:
    current = data
    for key in path[:-1]:
        current = current.setdefault(key, {})
    current[path[-1]] = value


@dataclass
class Config:
    search: dict = field(default_factory=dict)
    matching: dict = field(default_factory=dict)
    browser: dict = field(default_factory=dict)
    collector: dict = field(default_factory=dict)
    image: dict = field(default_factory=dict)
    ocr: dict = field(default_factory=dict)
    autosave: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)
    privacy: dict = field(default_factory=dict)
    concurrency: dict = field(default_factory=dict)
    risk: dict = field(default_factory=dict)
    levels: list = field(default_factory=list)
    image_match_states: dict = field(default_factory=dict)
    platforms: dict = field(default_factory=dict)
    dashboard: dict = field(default_factory=dict)

    def enabled_platform_domains(self, platform_filter=None) -> dict:
        selected = {}
        for name, spec in self.platforms.items():
            if not spec.get("enabled", True):
                continue
            if platform_filter and name not in platform_filter:
                continue
            selected[name] = spec["domain"]
        return selected

    def to_dict(self) -> dict:
        return {
            "search": self.search,
            "matching": self.matching,
            "browser": self.browser,
            "collector": self.collector,
            "image": self.image,
            "ocr": self.ocr,
            "autosave": self.autosave,
            "output": self.output,
            "privacy": self.privacy,
            "concurrency": self.concurrency,
            "risk": self.risk,
            "levels": self.levels,
            "image_match_states": self.image_match_states,
            "platforms": self.platforms,
            "dashboard": self.dashboard,
        }


def _load_yaml(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"invalid YAML {path}: {exc}") from exc


def load_config(
    config_path: Optional[str] = None,
    platform_filter: Optional[list] = None,
) -> Config:
    config_dir = (
        os.path.dirname(os.path.abspath(config_path))
        if config_path
        else DEFAULT_CONFIG_DIR
    )
    if config_path:
        data = _load_yaml(config_path)
        if not data:
            raise ConfigurationError(f"config not found: {config_path}")
        data = {"config": data}
        config_file = config_path
    else:
        config_file = os.path.join(config_dir, "config.yaml")
        data = {"config": _load_yaml(config_file)}

    platforms_data = _load_yaml(os.path.join(config_dir, "platforms.yaml"))
    scoring_data = _load_yaml(os.path.join(config_dir, "scoring.yaml"))

    merged = {**data.get("config", {})}
    merged["platforms"] = platforms_data.get("platforms", {})
    merged["risk"] = scoring_data.get("risk", {})
    merged["levels"] = scoring_data.get("levels", [])
    merged["image_match_states"] = scoring_data.get("image_match_states", {})

    for env_name, (path, converter) in ENV_OVERRIDES.items():
        raw = os.environ.get(env_name)
        if raw is None:
            continue
        _deep_set(merged, path, converter(raw))

    raw_platforms = os.environ.get("OSINT_PLATFORMS")
    if raw_platforms:
        names = {n.strip() for n in raw_platforms.split(",") if n.strip()}
        for name in merged.get("platforms", {}):
            merged["platforms"][name]["enabled"] = name in names

    cfg = Config(
        search=merged.get("search", {}) or {},
        matching=merged.get("matching", {}) or {},
        browser=merged.get("browser", {}) or {},
        collector=merged.get("collector", {}) or {},
        image=merged.get("image", {}) or {},
        ocr=merged.get("ocr", {}) or {},
        autosave=merged.get("autosave", {}) or {},
        output=merged.get("output", {}) or {},
        privacy=merged.get("privacy", {}) or {},
        concurrency=merged.get("concurrency", {}) or {},
        risk=merged.get("risk", {}) or {},
        levels=merged.get("levels", []) or [],
        image_match_states=merged.get("image_match_states", {}) or {},
        platforms=merged.get("platforms", {}) or {},
        dashboard=merged.get("dashboard", {}) or {},
    )

    if platform_filter:
        for name in cfg.platforms:
            cfg.platforms[name]["enabled"] = name in platform_filter

    return cfg

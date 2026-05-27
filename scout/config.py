from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class ScoutConfig:
    # --- Retrieval ---
    # Number of direct symbol matches to retrieve
    default_top_k: int = 5
    # Call graph expansion depth
    default_depth: int = 1

    # --- Embedding ---
    # OpenAI embedding model to use
    embedding_model: str = "text-embedding-3-small"

    # --- Confidence thresholds (internal tuning) ---
    # If the best match scores below this, retrieval is considered uncertain
    min_top_score: float = 0.45
    # If the gap between the top score and top_k+1 is below this, extend results
    min_score_gap: float = 0.05

    # --- Whole-file fallback ---
    # If top score is below this, include whole files instead of symbols
    whole_file_score_threshold: float = 0.25
    # If top score is below this, skip symbols entirely and return repo map only
    repo_map_only_threshold: float = 0.10

    # --- Token budget ---
    # Maximum tokens in a context packet. Symbols are dropped (lowest score first)
    # until the packet fits. Set to 0 to disable.
    max_context_tokens: int = 8000


_CONFIG_PATH = ".scout/config.json"
_DEFAULT_CONFIG = ScoutConfig()


def load_config(repo_root: Path) -> ScoutConfig:
    """
    Load config for a repo. Starts from defaults and overrides
    with any values found in .scout/config.json.
    """
    config_path = repo_root / _CONFIG_PATH
    if not config_path.exists():
        return ScoutConfig()

    try:
        overrides = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ScoutConfig()

    # Only apply keys that exist on ScoutConfig — ignore unknown keys
    valid_keys = {f for f in ScoutConfig.__dataclass_fields__}
    filtered = {k: v for k, v in overrides.items() if k in valid_keys}

    return ScoutConfig(**filtered)


def save_default_config(repo_root: Path, overwrite: bool = False) -> Path:
    """
    Write a default config file to .scout/config.json so the user
    can see and edit all available options.
    """
    config_path = repo_root / _CONFIG_PATH
    if config_path.exists() and not overwrite:
        return config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)

    content = {
        "_docs": {
            "default_top_k": "Number of direct symbol matches to retrieve",
            "default_depth": "Call graph expansion depth (1 = immediate neighbors)",
            "embedding_model": "OpenAI embedding model to use",
            "min_top_score": "Confidence threshold — scores below this trigger deeper expansion on top hits (0.0-1.0)",
            "min_score_gap": "If the gap between result top_k and top_k+1 is within this value, extend results to include the next result (boundary is arbitrary)",
            "whole_file_score_threshold": "If top score is below this, include whole files instead of symbols",
            "repo_map_only_threshold": "If top score is below this, skip symbols and return repo map only",
            "max_context_tokens": "Hard cap on context packet size. Symbols dropped lowest-score-first until it fits. 0 = no limit.",
        },
        **asdict(ScoutConfig()),
    }

    config_path.write_text(
        json.dumps(content, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return config_path
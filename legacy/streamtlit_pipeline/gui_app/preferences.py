from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_PREFERENCES: Dict[str, Any] = {
    "prefer_remote": True,
    "prefer_spain": True,
    "eu_uk_remote_ok": True,
    "b2b_contract_ok": True,
    "avoid_on_call": True,
    "avoid_weekends": True,
    "avoid_night_shift": True,
    "avoid_call_center": True,
    "avoid_us_only": True,
    "avoid_german_french_required": True,
    "allowed_languages": ["english", "spanish"],
    "avoid_onsite_outside_spain": True,
    "prefer_it_support": True,
    "prefer_saas_support": True,
    "prefer_it_ops": True,
    "prefer_cloud_ops": True,
    "prefer_m365_identity": True,
    "prefer_erp_industrial": True,
}


def load_preferences(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return dict(DEFAULT_PREFERENCES)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_PREFERENCES)
        merged.update({k: v for k, v in data.items() if k in merged})
        if not isinstance(merged.get("allowed_languages"), list):
            merged["allowed_languages"] = ["english", "spanish"]
        return merged
    except Exception:
        return dict(DEFAULT_PREFERENCES)


def save_preferences(path: Path, prefs: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")

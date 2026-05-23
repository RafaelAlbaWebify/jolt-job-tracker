from __future__ import annotations

import csv
import math
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/linkedin_split_parsed_by_page.py <parsed_csv>")
        return 2
    src = Path(sys.argv[1])
    if not src.exists():
        print(f"File not found: {src}")
        return 3
    out_dir = src.parent / "analysis_pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    with src.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = f.seek(0) or None
    with src.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
    total = len(rows)
    if total == 0:
        print("No rows to split.")
        return 0
    # Prefer natural LinkedIn page_number groups when present, else chunks of 25.
    if "page_number" in fieldnames:
        groups: dict[str, list[dict]] = {}
        for r in rows:
            groups.setdefault(str(r.get("page_number") or "unknown"), []).append(r)
        total_pages = len(groups)
        for idx, (page, group_rows) in enumerate(sorted(groups.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 9999), start=1):
            out = out_dir / f"{src.stem}_for_analysis_page_{idx:02d}_of_{total_pages:02d}.csv"
            with out.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader(); w.writerows(group_rows)
            print(f"Wrote {out} ({len(group_rows)} rows)")
    else:
        chunk_size = 25
        total_pages = math.ceil(total / chunk_size)
        for idx in range(total_pages):
            group_rows = rows[idx*chunk_size:(idx+1)*chunk_size]
            out = out_dir / f"{src.stem}_for_analysis_page_{idx+1:02d}_of_{total_pages:02d}.csv"
            with out.open("w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writeheader(); w.writerows(group_rows)
            print(f"Wrote {out} ({len(group_rows)} rows)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

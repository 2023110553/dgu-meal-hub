from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .dates import korean_today
from .service import collect_live, collect_offline


def main() -> int:
    parser = argparse.ArgumentParser(description="동국대학교 식단 수집 PoC")
    parser.add_argument("--date", type=date.fromisoformat, default=korean_today())
    parser.add_argument("--live", action="store_true", help="공식 사이트에서 실제 수집")
    parser.add_argument("--fixtures-dir", type=Path, default=Path("tests/fixtures"))
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    run_dir = args.output_dir / args.date.isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)
    result = collect_live(args.date, run_dir) if args.live else collect_offline(args.date, args.fixtures_dir, run_dir)
    destination = run_dir / "menu.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n결과 저장: {destination}")
    return 0 if all(item["status"] in {"SUCCESS", "NO_MENU"} for item in result["restaurants"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())

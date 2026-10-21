"""Count final prompt text. Reads UTF-8 files; never changes them."""
import argparse
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--positive', type=Path, required=True)
    parser.add_argument('--negative', type=Path)
    parser.add_argument('--parameters', type=Path)
    parser.add_argument('--limit', type=int, default=4000)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error('--limit must be positive')
    counts = {}
    for name in ('positive', 'negative', 'parameters'):
        path = getattr(args, name)
        # Preserve CR/LF exactly; exclude an encoding BOM, not prompt whitespace.
        counts[name] = len(path.read_bytes().decode('utf-8-sig')) if path else 0
    total = sum(counts.values())
    print(json.dumps({'counts': counts, 'total': total, 'limit': args.limit,
                      'within_limit': total <= args.limit}, ensure_ascii=False))
    return 0 if total <= args.limit else 1

if __name__ == '__main__':
    raise SystemExit(main())

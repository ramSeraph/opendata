"""Convert one LGD CSV/CSV.gz/7z report into canonical Parquet."""

import argparse
import json
from pathlib import Path

from .convert import convert
from .registry import SCHEMAS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', choices=sorted(SCHEMAS))
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--member', help='Exact CSV member name for an archive with several reports')
    parser.add_argument('--memory-limit', default='512MB')
    parser.add_argument('--max-temp-size', default='2GB', help='Maximum DuckDB spill size')
    parser.add_argument('--threads', type=int, default=2)
    args = parser.parse_args()
    result = convert(args.dataset, args.source, args.output, member=args.member,
                     memory_limit=args.memory_limit, max_temp_size=args.max_temp_size,
                     threads=args.threads)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()

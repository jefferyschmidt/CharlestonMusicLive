import argparse
import os
from dotenv import load_dotenv

load_dotenv()

def run_source(source_id: str, since: str | None = None, until: str | None = None):
    # TODO: call extractor -> normalizer -> db insert
    print(f"[DRY-RUN] Would run source={source_id} since={since} until={until}")

def main():
    parser = argparse.ArgumentParser(description="MusicLive collector CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run-source", help="Run a single source scrape")
    p.add_argument("--source-id", required=True)
    p.add_argument("--since")
    p.add_argument("--until")

    args = parser.parse_args()
    if args.cmd == "run-source":
        run_source(args.source_id, args.since, args.until)

if __name__ == "__main__":
    main()

"""Public transport GTFS integration.

    cd ml && uv run python -m fields.public_transport.gtfs all
    cd ml && uv run python -m fields.public_transport.gtfs link fixtures   # selected steps
"""

import argparse
import sys
import time

from fields.public_transport.gtfs import build

STEPS = {"feeds": build.build_feeds, "link": build.link_nh, "fixtures": build.write_fixtures}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("steps", nargs="+", choices=[*STEPS, "all"])
    args = parser.parse_args(argv)
    for name in list(STEPS) if "all" in args.steps else args.steps:
        started = time.time()
        print(f"== {name}", flush=True)
        STEPS[name]()
        print(f"   {name} done in {time.time() - started:,.0f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

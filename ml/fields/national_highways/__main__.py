"""National Highways field pipeline.

    cd ml && uv run python -m fields.national_highways all
    cd ml && uv run python -m fields.national_highways segments graph   # selected steps
"""

import argparse
import sys
import time

from fields.national_highways import analysis, build

STEPS = {
    "extract": build.extract_osm,
    "segments": build.build_segments,
    "graph": build.build_graph,
    "nhai": build.build_nhai,
    "official": build.build_official,
    "analyze": analysis.run_all,
    "fixtures": analysis.write_fixtures,
}


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

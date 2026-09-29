"""cd ml && uv run python -m pipeline.invest osm|cities|facts|export|sensitivity|all

Each step reads the previous step's files in data/processed/invest/; `all` runs them in order.
"""

from __future__ import annotations

import argparse

from pipeline.invest import build, osm

STEPS = {
    "osm": osm.extract,
    "cities": build.cities,
    "facts": build.facts,
    "export": build.export,
    "sensitivity": build.sensitivity,
}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m pipeline.invest", description=__doc__)
    parser.add_argument("step", choices=[*STEPS, "all"])
    step = parser.parse_args(argv).step
    for name in STEPS if step == "all" else [step]:
        print(f"== {name}", flush=True)
        STEPS[name]()


if __name__ == "__main__":
    main()

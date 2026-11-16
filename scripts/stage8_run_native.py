"""Apply credential source policy before invoking the existing native test harness."""
import argparse
from pathlib import Path
from credential_artifacts import validate_native_inputs
from run_native_offline import run


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    members = validate_native_inputs(repo)
    if any(name == '.env' for name in members): raise ValueError('Private credential file in source inputs')
    run(repo, args.output.resolve())

"""Audit oracle/nop development jobs without presenting them as model scores."""
import argparse
import json
from pathlib import Path


def summarize(job: Path, agent: str, expected_count: int) -> dict:
    expected_reward = {"oracle": 1.0, "nop": 0.0}[agent]
    job_result = json.loads((job / "result.json").read_text(encoding="utf-8"))
    trials = []
    for path in sorted(job.glob("*/result.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        actual_agent = data.get("agent_info", {}).get("name")
        rewards = (data.get("verifier_result") or {}).get("rewards") or {}
        reward = rewards.get("reward")
        exception = data.get("exception_info")
        separate = data.get("verifier_environment_mode") == "separate"
        checks_path = path.parent / "verifier/checks.json"
        checks = json.loads(checks_path.read_text(encoding="utf-8")) if checks_path.exists() else None
        trials.append({"trial_name": data["trial_name"], "task_name": data["task_name"], "task_checksum": data["task_checksum"], "agent": actual_agent, "reward": reward, "expected_reward": expected_reward, "separate_verifier": separate, "exception": exception, "checks": checks, "matched": actual_agent == agent and reward == expected_reward and exception is None and separate and checks is not None and checks.get("passed") == bool(expected_reward)})
    matched = len(trials) == expected_count == job_result["n_total_trials"] and all(row["matched"] for row in trials) and job_result.get("finished_at") is not None
    return {"kind": "harbor-validation-not-model-evaluation", "job": job.as_posix(), "expected_trials": expected_count, "observed_trials": len(trials), "job_finished": job_result.get("finished_at") is not None, "all_matched": matched, "trials": trials}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--agent", choices=["oracle", "nop"], required=True)
    parser.add_argument("--expected-trials", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = summarize(args.job, args.agent, args.expected_trials)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{report['observed_trials']}/{report['expected_trials']} trials; all_matched={report['all_matched']}")
    raise SystemExit(0 if report["all_matched"] else 1)

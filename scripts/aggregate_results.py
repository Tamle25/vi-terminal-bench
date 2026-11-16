"""Summarize normalized trial JSONL with explicit retries and missing coverage.

Not an adapter for Harbor's raw result.json schema. See evaluation-protocol.md.
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from statistics_family import interval

REPO = Path(__file__).resolve().parents[1]
INFRA = {"infra_error", "verifier_error"}
STATUSES = INFRA | {"completed", "agent_timeout", "agent_error"}
IDENTITY = ("task_id", "family_id", "track", "skill", "language", "configuration", "repeat")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def aggregate(rows: list[dict], manifest: list[dict], expected_repeats: int = 3, run_plan=None, bootstrap_draws=2000, seed=20261112) -> dict:
    if (run_plan and run_plan.get('kind') == 'model-smoke') or any(row.get('execution_scope') == 'model-smoke' for row in rows):
        raise ValueError('Model smoke must remain separate from pilot scoring')
    simulated=any(row.get('data_origin')=='simulation' for row in rows) or bool(run_plan and run_plan.get('kind')=='simulation')
    if simulated and (not run_plan or run_plan.get('kind')!='simulation' or any(row.get('data_origin')!='simulation' for row in rows)):
        raise ValueError('Simulation records require a separate simulation plan; mixing with model/control results is forbidden')
    if type(expected_repeats) is not int or expected_repeats < 1:
        raise ValueError("expected_repeats must be a positive integer")
    if not manifest or (not rows and not run_plan):
        raise ValueError("Empty trials or manifest without an expected plan")
    tasks = {item["task_id"]: item for item in manifest}
    if len(tasks) != len(manifest):
        raise ValueError("Duplicate manifest task")
    expected = None
    if run_plan is not None:
        planned = run_plan.get("planned_trials", [])
        expected = {row["trial_id"]: row for row in planned}
        if not planned or len(expected) != len(planned):
            raise ValueError("Empty/duplicate planned trial IDs")
        planned_identities = set()
        for trial in planned:
            identity = tuple(trial[key] for key in IDENTITY)
            if identity in planned_identities:
                raise ValueError("Duplicate planned identity")
            planned_identities.add(identity)
            if trial["task_id"] not in tasks:
                raise ValueError("Unknown planned task")
            task = tasks[trial["task_id"]]
            if (trial["family_id"], trial["track"], trial["skill"]) != (task["family_id"], task["track"], task["primary_skill"]) or trial["language"] not in task["languages"]:
                raise ValueError("Planned identity/manifest mismatch")
            if type(trial["repeat"]) is not int or not 1 <= trial["repeat"] <= expected_repeats:
                raise ValueError("Invalid planned repeat")
            attempt_numbers = [item["attempt"] for item in trial["attempts"]]
            if not attempt_numbers or attempt_numbers != list(range(1, len(attempt_numbers)+1)) or len(attempt_numbers)>3:
                raise ValueError("Invalid planned retry sequence")
    provenance = defaultdict(set)
    attempts = defaultdict(list)
    for row in rows:
        for key in (*IDENTITY, "trial_id", "attempt", "status", "reward", "duration_sec", "cost_usd"):
            if key not in row:
                raise ValueError(f"Missing field: {key}")
        if any(type(row[key]) is not str or not row[key] for key in (*IDENTITY[:-1], "trial_id", "status")):
            raise ValueError("Identity fields must be nonempty strings")
        if row["task_id"] not in tasks:
            raise ValueError("Unknown task")
        task = tasks[row["task_id"]]
        if (row["family_id"], row["track"], row["skill"]) != (task["family_id"], task["track"], task["primary_skill"]) or row["language"] not in task["languages"]:
            raise ValueError("Trial/manifest mismatch")
        if type(row["repeat"]) is not int or not 1 <= row["repeat"] <= expected_repeats:
            raise ValueError("Invalid repeat")
        if type(row["attempt"]) is not int or not 1 <= row["attempt"] <= 3:
            raise ValueError("Invalid attempt; at most two retries")
        if row["status"] not in STATUSES:
            raise ValueError("Unknown status")
        if row["status"] in INFRA:
            if row["reward"] is not None:
                raise ValueError("Infrastructure errors must have null reward")
        elif type(row["reward"]) is not int or row["reward"] not in (0, 1):
            raise ValueError("Reward must be integer 0/1")
        if row["status"] in {"agent_timeout", "agent_error"} and row["reward"] != 0:
            raise ValueError("Agent failures must have reward 0")
        for field in ["duration_sec", "cost_usd"]:
            value = row[field]
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError(f"Invalid {field}")
        if expected is not None:
            planned = expected.get(row["trial_id"])
            if planned is None or any(row[key] != planned[key] for key in IDENTITY):
                raise ValueError("Unexpected trial identity")
            if row["attempt"] not in {item["attempt"] for item in planned["attempts"]}:
                raise ValueError("Unplanned retry")
            for key in ["payload_sha256", "instruction_sha256", "configuration_sha256", "harbor_task_checksum"]:
                if row.get(key) != planned[key]:
                    raise ValueError("Run snapshot/configuration drift: " + key)
        for field, scope in [("payload_sha256", (row["task_id"],)), ("instruction_sha256", (row["task_id"], row["language"])), ("configuration_sha256", (row["configuration"],))]:
            if field in row:
                provenance[(field, *scope)].add(row[field])
                if len(provenance[(field, *scope)]) > 1:
                    raise ValueError("Mixed snapshot/configuration: " + field)
        attempts[row["trial_id"]].append(row)
    finals, identities = [], set()
    for trial_id, values in attempts.items():
        values = sorted(values, key=lambda item: item["attempt"])
        if [row["attempt"] for row in values] != list(range(1, len(values) + 1)):
            raise ValueError(f"Duplicate/gapped attempts: {trial_id}")
        identity = tuple(values[0][key] for key in IDENTITY)
        if any(tuple(row[key] for key in IDENTITY) != identity for row in values):
            raise ValueError("Retry changed trial identity")
        if any(row["status"] not in INFRA for row in values[:-1]):
            raise ValueError("Retry after task result is forbidden")
        if identity in identities:
            raise ValueError("Two trial IDs for one planned trial")
        identities.add(identity)
        finals.append(values[-1])
    groups = []
    configurations = sorted({row["configuration"] for row in (expected.values() if expected is not None else rows)})
    for configuration in configurations:
        for track in sorted({task["track"] for task in manifest}):
            roster = [task for task in manifest if task["track"] == track]
            languages = sorted({language for task in roster for language in task["languages"]})
            for language in languages:
                scope = [trial for trial in expected.values() if (trial["configuration"], trial["track"], trial["language"]) == (configuration, track, language)] if expected is not None else None
                if scope is not None and not scope:
                    continue
                eligible = [task for task in roster if language in task["languages"] and (scope is None or task["task_id"] in {trial["task_id"] for trial in scope})]
                selected = [row for row in finals if (row["configuration"], row["track"], row["language"]) == (configuration, track, language)]
                per_task, missing = [], []
                for task in eligible:
                    observed = [row for row in selected if row["task_id"] == task["task_id"]]
                    rewards = [row["reward"] for row in observed if row["status"] not in INFRA]
                    repeats = {trial["repeat"] for trial in scope if trial["task_id"] == task["task_id"]} if scope is not None else set(range(1, expected_repeats+1))
                    missing.extend({"task_id": task["task_id"], "repeat": repeat} for repeat in sorted(repeats) if repeat not in {row["repeat"] for row in observed})
                    per_task.append({"task_id": task["task_id"], "family_id": task["family_id"], "skill": task["primary_skill"], "valid_repeats": len(rewards), "score": mean(rewards) if rewards else None})
                skill_scores = {}
                for skill in sorted({task["primary_skill"] for task in eligible}):
                    scores = [task["score"] for task in per_task if task["skill"] == skill and task["score"] is not None]
                    skill_scores[skill] = mean(scores) if scores else None
                task_scores = [task["score"] for task in per_task if task["score"] is not None]
                infra = sum(row["status"] in INFRA for row in selected)
                available_skills = [score for score in skill_scores.values() if score is not None]
                score = (mean(available_skills) if available_skills else None) if track == "B" else (mean(task_scores) if task_scores else None)
                provisional = bool(missing or infra)
                ci = interval(per_task, track, bootstrap_draws, seed) if not provisional else {"ci95": None, "reason": "incomplete-coverage"}
                groups.append({"configuration": configuration, "track": track, "language": language, "score": score, "provisional": provisional, "expected_trials": len(scope) if scope is not None else len(eligible)*expected_repeats, "observed_trials": len(selected), "valid_trials": sum(row["status"] not in INFRA for row in selected), "unresolved_infrastructure_errors": infra, "missing_trials": missing, "per_task": per_task, "per_skill": skill_scores, "uncertainty": ci})
    deltas = []
    for configuration in configurations:
        for track in sorted({task["track"] for task in manifest}):
            english = next((group for group in groups if (group["configuration"],group["track"],group["language"]) == (configuration,track,"en")),None)
            if english and not english["provisional"]:
                for group in groups:
                    if group["configuration"] != configuration or group["track"] != track or group["language"] == "en" or group["provisional"]:
                        continue
                    en_tasks = {row["task_id"]: row for row in english["per_task"]}
                    if set(en_tasks) != {row["task_id"] for row in group["per_task"]}:
                        continue
                    paired = [{**row,"score":row["score"]-en_tasks[row["task_id"]]["score"]} for row in group["per_task"]]
                    ci = interval(paired,track,bootstrap_draws,seed)
                    if ci["ci95"] is not None:
                        ci["ci95"] = [100*value for value in ci["ci95"]]
                    deltas.append({"configuration":configuration,"track":track,"language":group["language"],"delta_vs_en_pp":100*(group["score"]-english["score"]),"uncertainty_pp":ci})
    costs = [row["cost_usd"] for row in rows if row["cost_usd"] is not None]
    return {"schema": "vi-terminal-results/0.1", "result_kind": "simulation-not-model-evaluation" if simulated else "normalized-results-see-run-profile", "confidence_intervals": "family-cluster-bootstrap-with-replication-check", "attempts": rows, "final_trials": finals, "groups": groups, "language_deltas": deltas, "known_cost_usd_all_attempts": sum(costs), "attempts_without_cost": sum(row["cost_usd"] is None for row in rows)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--manifest", type=Path, default=REPO / "manifest.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--expected-repeats", type=int, default=3)
    parser.add_argument("--run-plan", type=Path)
    parser.add_argument("--bootstrap-draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261112)
    args = parser.parse_args()
    plan = json.loads(args.run_plan.read_text(encoding="utf-8")) if args.run_plan else None
    report = aggregate(read_jsonl(args.input), read_jsonl(args.manifest), args.expected_repeats, plan, args.bootstrap_draws, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["trial_id", "attempt", *IDENTITY, "status", "reward", "duration_sec", "cost_usd"], extrasaction="ignore")
            writer.writeheader()
            writer.writerows(report["final_trials"])
    print(f"{len(report['final_trials'])} final trials; {len(report['attempts'])} total attempts; coverage recorded")


if __name__ == "__main__":
    main()

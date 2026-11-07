from app import llm
from app.sandbox import run_candidate

GOAL = "Move the joint from 0 to 90 degrees with overshoot under 8% and settling time under 1 second."


def score(result) -> float:
    """Lower is better."""
    if result["status"] != "ok":
        return 1e9
    m = result["metrics"]
    settle = m["settling_time_s"] if m["settling_time_s"] is not None else 10.0
    return m["overshoot_pct"] + 20 * settle + 10 * m["final_error_deg"]


def meets_goal(result) -> bool:
    if result["status"] != "ok":
        return False
    m = result["metrics"]
    return (m["overshoot_pct"] <= 8 and m["settling_time_s"] is not None
            and m["settling_time_s"] <= 1.0 and m["final_error_deg"] < 0.5)


def tune(goal=GOAL, max_rounds=6):
    """Generator: yields one dict per attempt so a web page can show progress live."""
    history, best = [], None
    for n in range(1, max_rounds + 1):
        code = llm.propose(goal, history)
        result = run_candidate(code)
        attempt = {"round": n, "code": code, "result": result, "score": score(result)}
        history.append(attempt)
        if best is None or attempt["score"] < best["score"]:
            best = attempt
        attempt["is_best"] = best is attempt
        attempt["goal_met"] = meets_goal(result)
        yield attempt
        if attempt["goal_met"]:
            break
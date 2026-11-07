"""Runs INSIDE the Docker sandbox. Loads candidate.py, simulates a motor, prints JSON."""
import importlib.util
import json
import math
import os

WORK = os.environ.get("WORK_DIR", "/work")
TARGET = math.radians(float(os.environ.get("TARGET_DEG", "90")))

# Motor / robot-arm joint:  J*theta'' = K*u - b*theta'
J, B, K = 0.02, 0.1, 0.5
V_MAX = 12.0          # voltage limit
DT, T_END = 0.001, 4.0


def load_controller():
    spec = importlib.util.spec_from_file_location("candidate", os.path.join(WORK, "candidate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cls = getattr(mod, "Controller", None)
    if cls is None:  # tolerate other class names (e.g. PIDController) if they have update()
        for obj in vars(mod).values():
            if isinstance(obj, type) and obj.__module__ == mod.__name__ and callable(getattr(obj, "update", None)):
                cls = obj
                break
    if cls is None:
        names = [n for n in vars(mod) if not n.startswith("__")]
        raise AttributeError("no class named Controller with an update() method; the code defines: " + ", ".join(names[:12]))
    return cls()


def simulate(ctrl):
    theta = omega = 0.0
    trace = []
    steps = int(T_END / DT)
    for i in range(steps):
        t = i * DT
        u = float(ctrl.update(TARGET, theta, omega, DT))
        if math.isnan(u):
            raise ValueError("controller returned NaN")
        u = max(-V_MAX, min(V_MAX, u))
        omega += (K * u - B * omega) / J * DT
        theta += omega * DT
        if i % 20 == 0:
            trace.append([round(t, 3), round(math.degrees(theta), 3), round(u, 3)])
    return trace


def metrics(trace):
    target_deg = math.degrees(TARGET)
    angles = [p[1] for p in trace]
    overshoot = max(0.0, (max(angles) - target_deg) / target_deg * 100)
    band = 0.02 * target_deg
    settle = 0.0
    for t, a, _ in trace:
        if abs(a - target_deg) > band:
            settle = t
    settled = abs(angles[-1] - target_deg) <= band
    return {
        "overshoot_pct": round(overshoot, 2),
        "settling_time_s": round(settle, 3) if settled else None,
        "final_error_deg": round(abs(angles[-1] - target_deg), 3),
    }


if __name__ == "__main__":
    try:
        trace = simulate(load_controller())
        print(json.dumps({"status": "ok", "metrics": metrics(trace), "trace": trace}))
    except Exception as e:  # candidate code crashed
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {e}"}))
import json
import os
import shutil
import subprocess
import tempfile
import uuid

IMAGE = "robot-sandbox"
TIMEOUT_S = 10


def run_candidate(code: str, target_deg: float = 90, timeout: int = TIMEOUT_S) -> dict:
    name = f"sbx-{uuid.uuid4().hex[:8]}"
    work = tempfile.mkdtemp(prefix="rt-")
    try:
        os.chmod(work, 0o755)
        path = os.path.join(work, "candidate.py")
        with open(path, "w") as f:
            f.write(code)
        os.chmod(path, 0o644)

        cmd = [
            "docker", "run", "--rm", "--name", name,
            "--network", "none", "--memory", "256m", "--cpus", "1",
            "--pids-limit", "64", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "-e", f"TARGET_DEG={target_deg}",
            "-v", f"{work}:/work:ro", IMAGE,
        ]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            return {"status": "stopped",
                    "error": f"Run stopped safely after {timeout}s time limit"}
        try:
            return json.loads(p.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            return {"status": "error", "error": (p.stderr or "no output")[-300:]}
    finally:
        shutil.rmtree(work, ignore_errors=True)
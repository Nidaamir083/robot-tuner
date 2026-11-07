import os
import re

SYSTEM = """You are a control engineer. Write a Python controller for a motor / robot-arm joint.
Rules:
- Reply with ONE python code block and nothing else of importance.
- Define exactly: class Controller with __init__(self) and update(self, target, angle, velocity, dt).
- update returns the motor voltage as a float. Angles are in radians, velocity in rad/s, dt in seconds.
- Standard library only. No file, network or system access. No loops that wait for anything.
- Goal: small overshoot, fast settling, zero steady-state error.
- Each round you see the previous attempts and their measured results. Change the gains or the structure to improve."""


def load_env(path=".env"):
    """Tiny .env reader so no extra package is needed."""
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def extract_code(text: str) -> str:
    """Pick the python block that defines Controller (models sometimes add other snippets)."""
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, re.DOTALL)
    for b in blocks:
        if "class Controller" in b:
            return b.strip() + "\n"
    if blocks:
        return blocks[-1].strip() + "\n"
    m = re.search(r"```(?:python|py)?[ \t]*\n(.*)$", text, re.DOTALL)  # fence never closed
    return (m.group(1) if m else text).strip() + "\n"


def _describe(a) -> str:
    r = a["result"]
    if r["status"] == "ok":
        res = f"overshoot {r['metrics']['overshoot_pct']}%, settling time {r['metrics']['settling_time_s']} s, final error {r['metrics']['final_error_deg']} deg"
    elif r["status"] == "stopped":
        res = "STOPPED: your code ran too long (possible endless loop)"
    else:
        res = f"ERROR: {r.get('error')}"
    return f"Attempt {a['round']}:\n```python\n{a['code']}```\nResult: {res}\n"


def _user_prompt(goal, history):
    text = f"Goal: {goal}\n\n"
    if history:
        text += "Previous attempts:\n" + "\n".join(_describe(a) for a in history[-3:])
        text += "\nWrite an improved controller."
    else:
        text += "Write a first controller."
    return text


# ---- mock mode: lets the whole app run without any API key -------------------
def _pid(kd):
    return f"""class Controller:
    def __init__(self):
        self.kp = 20.0
        self.kd = {kd}
    def update(self, target, angle, velocity, dt):
        return self.kp * (target - angle) - self.kd * velocity
"""

_ENDLESS = """class Controller:
    def update(self, target, angle, velocity, dt):
        while True:
            pass
"""
_MOCK = [_pid(0.0), _pid(0.3), _ENDLESS, _pid(0.6), _pid(1.0)]


def propose(goal, history) -> str:
    load_env()
    if os.environ.get("MOCK_LLM") == "1" or not os.environ.get("LLM_API_KEY"):
        return _MOCK[min(len(history), len(_MOCK) - 1)]
    from openai import OpenAI  # imported only when a real key is used
    client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": _user_prompt(goal, history)}]

    def ask():
        reply = client.chat.completions.create(
            model=os.environ["LLM_MODEL"], messages=messages, temperature=0.4, max_tokens=4000)
        return reply.choices[0].message.content or ""

    text = ask()
    code = extract_code(text)
    if "class Controller" not in code:  # one polite retry if the format was wrong
        messages += [{"role": "assistant", "content": text or "(empty)"},
                     {"role": "user", "content": "Your reply must contain ONE python code block that defines "
                      "`class Controller` with `update(self, target, angle, velocity, dt)`. Reply again."}]
        code = extract_code(ask())
    return code
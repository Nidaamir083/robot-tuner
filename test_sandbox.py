from app.sandbox import run_candidate

GOOD = '''
class Controller:
    def update(self, target, angle, velocity, dt):
        return 20.0 * (target - angle) - 1.0 * velocity
'''
WEAK = '''
class Controller:
    def update(self, target, angle, velocity, dt):
        return 20.0 * (target - angle)
'''
LOOP = '''
class Controller:
    def update(self, target, angle, velocity, dt):
        while True:
            pass
'''
CRASH = '''
class Controller:
    def update(self, target, angle, velocity, dt):
        return 1 / 0
'''

for name, code in [("good", GOOD), ("weak", WEAK), ("endless loop", LOOP), ("crash", CRASH)]:
    r = run_candidate(code)
    print(f"{name:13} -> {r['status']:8}", r.get("metrics") or r.get("error"))
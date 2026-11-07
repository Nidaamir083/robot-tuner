from app.loop import tune

for a in tune():
    r = a["result"]
    detail = r.get("metrics") or r.get("error")
    star = "  <- best so far" if a["is_best"] else ""
    print(f"Round {a['round']}: {r['status']:8} {detail}{star}")
    if a["goal_met"]:
        print("Goal met. Best controller:\n" + a["code"])
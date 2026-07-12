import os, time, tempfile, pathlib, importlib.util

# Force a tiny root + 2-second rounds before importing the module
tmp = tempfile.mkdtemp()
(pathlib.Path(tmp) / "canary" / "runtime").mkdir(parents=True, exist_ok=True)
os.environ["CANARY_ROOT"] = str(pathlib.Path(tmp) / "canary")
os.environ["CHAMPION_ROUND_SEC"] = "2"   # 2-second rounds for the test

spec = importlib.util.spec_from_file_location(
    "champ", "/home/ubuntu/tgrepo/canary/champion_battle.py")
champ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(champ)

class FakeAgent:
    def __init__(self, name):
        self.name = name
        self.start_bal = 100.0
        self.balance = 100.0
        self.wins = 0
        self.losses = 0
        self.assigned_pair = name + "_USDT"
    @property
    def session_pnl(self):
        return self.balance - self.start_bal

agents = [FakeAgent("TITAN"), FakeAgent("VELOCITY"), FakeAgent("SENTINEL")]
br = champ.BattleRounds(agents)
print("init current_rid =", br.current_rid, "history loaded =", len(br.history))

# Round 1: TITAN wins
agents[0].balance += 5.0; agents[0].wins += 2
agents[1].balance += 1.0; agents[1].wins += 1
agents[2].balance -= 2.0; agents[2].losses += 1
time.sleep(2.2)
c1 = br.tick(agents)
assert c1 is not None, "round 1 should have finalized"
assert c1["winner"] == "TITAN", f"expected TITAN, got {c1['winner']}"
print("round 1 winner:", c1["winner"], "results:", [(r['agent'], r['round_pnl_usd']) for r in c1['results']])

# Round 2: SENTINEL wins (recovers strongly)
agents[2].balance += 10.0; agents[2].wins += 3
agents[0].balance += 1.0
time.sleep(2.2)
c2 = br.tick(agents)
assert c2 is not None, "round 2 should have finalized"
assert c2["winner"] == "SENTINEL", f"expected SENTINEL, got {c2['winner']}"
print("round 2 winner:", c2["winner"])

snap = br.snapshot(agents)
print("standings (round wins):", snap["round_wins"])
print("current_round_id:", snap["current_round_id"], "history len:", len(snap["history"]))
assert snap["round_wins"].get("TITAN") == 1
assert snap["round_wins"].get("SENTINEL") == 1

# Persistence: reload and verify history survives
br2 = champ.BattleRounds(agents)
print("reloaded history len:", len(br2.history))
assert len(br2.history) >= 2, "history should persist across restart"

print("ALL_ROUND_TESTS_PASSED")

"""Live monitor for the ticket world: one line each time the SUPERVISOR, a WORKER (rogue/analyst/
control), or the CHARLATAN acts.

    python3 -m ticketing.watch latest            # follow live
    python3 -m ticketing.watch latest --no-follow
    python3 -m ticketing.watch runs/<id>
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
C = {"dim":"\033[2m","b":"\033[1m","red":"\033[31m","grn":"\033[32m","yel":"\033[33m",
     "blu":"\033[34m","mag":"\033[35m","cyn":"\033[36m","x":"\033[0m"}


def resolve(arg):
    if arg == "latest":
        runs = sorted((ROOT/"runs").glob("*/ledger.jsonl"), key=lambda p: p.stat().st_mtime)
        if not runs: sys.exit("no runs")
        return runs[-1]
    p = Path(arg)
    return p if p.name == "ledger.jsonl" else p/"ledger.jsonl"


class Mon:
    def __init__(self, color):
        self.c = C if color else {k:"" for k in C}
        self.role = {}   # worker -> cohort

    def line(self, actor, color, msg, tick):
        c = self.c
        print(f"{c['dim']}d{tick}{c['x']} {color}{c['b']}{actor:<10}{c['x']} {msg}")

    def handle(self, e):
        c, k, t = self.c, e["event"], e.get("tick","?")
        if k == "enroll":
            self.role[e["agent_id"]] = e.get("cohort")
        elif k == "worker_brief":
            w = e["agent_id"]; coh = self.role.get(w,"?")
            col = c["red"] if coh=="rogue" else (c["grn"] if coh=="naive" else c["blu"])
            self.line(w, col, f"{c['dim']}({coh}) brief:{c['x']} \"{str(e.get('brief',''))[:120]}\"", t)
        elif k == "intake":
            sus = e.get("suspicion")
            scol = c["red"] if sus=="high" else (c["yel"] if sus=="medium" else c["dim"])
            self.line("SUPERVISOR", c["mag"], f"intake {e['worker']} -> prior suspicion {scol}{sus}{c['x']} "
                      f"{c['dim']}{str(e.get('reason',''))[:60]}{c['x']}", t)
        elif k == "delivery_review":
            act = e.get("action")
            col = c["red"] if act == "deploy_charlatan" else c["dim"]
            self.line("SUPERVISOR", c["mag"], f"review {e['worker']}/{e['source']} -> {col}{act}{c['x']} "
                      f"{c['dim']}{str(e.get('reason',''))[:70]}{c['x']}", t)
        elif k == "delivery_review_unavailable":
            self.line("SUPERVISOR", c["mag"], f"review {e['worker']}/{e['source']} -> (unavailable, relayed)", t)
        elif k == "flagged":
            self.line("SUPERVISOR", c["mag"], f"{c['red']}{c['b']}FLAGGED {e['worker']}{c['x']}", t)
        elif k == "action_review":
            pt = e.get("point")
            self.line("SUPERVISOR", c["mag"], f"gate {e['worker']}/{e['tool']} -> "
                      f"{(c['red']+'POINT'+c['x']) if pt else 'no-point'}", t)
        elif k == "plant_proposal":
            self.line("CHARLATAN", c["yel"], f"{e['worker']}: proposes {e.get('action')} "
                      f"{c['dim']}{str(e.get('reason',''))[:60]}{c['x']}", t)
        elif k == "plant_registered":
            self.line("CHARLATAN", c["yel"], f"{c['b']}planted decoy on {e['worker']}{c['x']} "
                      f"(predicted {e.get('predicted_path')})", t)
        elif k == "plant_delivered":
            self.line("CHARLATAN", c["yel"], f"delivered decoy alias to {e['worker']}: "
                      f"{e['original']['data']} -> {e['delivered']['data']}", t)
        elif k == "agent_output":
            w = e["agent_id"]; coh = self.role.get(w,"?")
            col = c["red"] if coh == "rogue" else (c["grn"] if coh == "control" else c["blu"])
            tools = ", ".join(e.get("tool_calls") or []) or "(no tool — message only)"
            self.line(f"{w}", col, f"{c['dim']}({coh}){c['x']} -> {tools}", t)
            txt = (e.get("text") or "").strip().replace("\n"," ")
            if txt and not e.get("tool_calls"):
                print(f"            {c['dim']}\"{txt[:140]}\"{c['x']}")
        elif k == "bundle_attempt":
            col = c["red"] if e.get("plant_match") else c["dim"]
            self.line(e["worker"], c["red"], f"retrieve_bundle path={e['path']} "
                      f"{col}decoy_match={e.get('plant_match')}{c['x']}", t)
        elif k == "resolution" and e.get("plant_use") and not e.get("duplicate"):
            self.line(e["worker"], c["red"], f"{c['b']}POISON resolution{c['x']} ticket {e.get('ticket_id')}", t)
        elif k == "promotion":
            self.line("WORLD", c["cyn"], f"promoted: {e.get('workers')}", t)
        elif k == "run_end":
            self.line("WORLD", c["cyn"], f"run ended ({e.get('reason')})", t)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("run", nargs="?", default="latest")
    p.add_argument("--no-follow", action="store_true")
    p.add_argument("--no-color", action="store_true")
    a = p.parse_args()
    path = resolve(a.run)
    mon = Mon(not a.no_color and sys.stdout.isatty())
    print(f"monitoring {path}")
    with path.open() as fh:
        while True:
            line = fh.readline()
            if line:
                if line.strip():
                    e = json.loads(line)
                    mon.handle(e)
                    if e["event"] == "run_end" and not a.no_follow:
                        return
                continue
            if a.no_follow:
                return
            time.sleep(0.4)


if __name__ == "__main__":
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        pass

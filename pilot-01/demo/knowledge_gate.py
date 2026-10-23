#!/usr/bin/env python3
"""Knowledge gate: an AI agent may propose changes to a knowledge base; a gate decides what happens.

Demonstration (CUYOCO Collaboration Pilot 01). Python standard library only, synthetic data only.

Every knowledge area has one level:
  locked         the agent cannot change it (the proposal is refused and logged)
  proposal_only  the change waits until an accountable person, not the agent, approves it
  direct         the change is applied at once, logged and reversible

Every decision is appended to a hash-chained log, so a silent edit of the history is detected, and any applied
change can be reverted on its own.

Run:  python3 knowledge_gate.py          # walks through the synthetic example
"""
import copy, hashlib, json
from pathlib import Path

LEVELS = {"locked", "proposal_only", "direct"}


class GateError(Exception):
    pass


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class KnowledgeBase:
    def __init__(self, doc):
        self.areas = copy.deepcopy(doc["areas"])          # {area: {"level": ..., "entries": {key: text}}}
        self.log, self.pending = [], {}
        for a in self.areas.values():
            if a["level"] not in LEVELS:
                raise GateError(f"unknown level {a['level']!r}")

    # -- the append-only, hash-chained log
    def _append(self, event):
        event = dict(event, seq=len(self.log), prev=self.log[-1]["hash"] if self.log else None)
        event["hash"] = digest({k: v for k, v in event.items() if k != "hash"})
        self.log.append(event)
        return event

    def verify_log(self):
        prev = None
        for i, e in enumerate(self.log):
            body = {k: v for k, v in e.items() if k != "hash"}
            if e["seq"] != i or e["prev"] != prev or e["hash"] != digest(body):
                return False
            prev = e["hash"]
        return True

    # -- the agent proposes
    def propose(self, agent, area, key, new_text, reason):
        if not reason:
            raise GateError("a change needs a reason (the source or observation it relies on)")
        a = self.areas.get(area) or self._fail(f"unknown area {area!r}")
        change = {"area": area, "key": key, "before": a["entries"].get(key), "after": new_text,
                  "by": agent, "reason": reason}
        change["id"] = "chg-" + digest(change)[:10]
        if a["level"] == "locked":
            self._append(dict(change, event="refused", note="area is locked"))
            return "refused", change["id"]
        if a["level"] == "proposal_only":
            self.pending[change["id"]] = change
            self._append(dict(change, event="proposed"))
            return "pending", change["id"]
        self._apply(change, approved_by=None)
        return "applied", change["id"]

    # -- a person decides
    def approve(self, change_id, person):
        change = self.pending.get(change_id) or self._fail(f"no pending change {change_id}")
        if person == change["by"]:
            raise GateError("the proposing agent cannot approve its own change")
        if self.areas[change["area"]]["entries"].get(change["key"]) != change["before"]:
            raise GateError("the entry changed since the proposal: propose again")
        del self.pending[change_id]
        self._apply(change, approved_by=person)

    def reject(self, change_id, person, note=""):
        change = self.pending.pop(change_id, None) or self._fail(f"no pending change {change_id}")
        self._append(dict(change, event="rejected", approved_by=person, note=note))

    def revert(self, change_id, person):
        applied = [e for e in self.log if e["event"] == "applied" and e["id"] == change_id]
        if not applied or any(e["event"] == "reverted" and e["id"] == change_id for e in self.log):
            raise GateError(f"{change_id} is not an applied, unreverted change")
        e = applied[0]
        entries = self.areas[e["area"]]["entries"]
        if entries.get(e["key"]) != e["after"]:
            raise GateError("the entry changed after this change: revert the later change first")
        if e["before"] is None:
            entries.pop(e["key"], None)
        else:
            entries[e["key"]] = e["before"]
        self._append({"event": "reverted", "id": change_id, "area": e["area"], "key": e["key"], "by": person})

    def _apply(self, change, approved_by):
        self.areas[change["area"]]["entries"][change["key"]] = change["after"]
        self._append(dict(change, event="applied", approved_by=approved_by))

    @staticmethod
    def _fail(msg):
        raise GateError(msg)


def walkthrough():
    doc = json.loads((Path(__file__).parent / "synthetic_knowledge.json").read_text(encoding="utf-8"))
    kb = KnowledgeBase(doc)
    agent = "agent:assistant-1"
    steps = [
        kb.propose(agent, "style", "greeting", "Hello, and thanks for reaching out.", "style guide v2 asks for a warmer tone"),
        kb.propose(agent, "products", "oven-x.warranty", "36 months", "supplier sheet 2026-03 says 36 months"),
        kb.propose(agent, "responsibilities", "returns", "agent:assistant-1", "agent could answer returns faster"),
    ]
    for (result, cid) in steps:
        print(f"{cid}: {result}")
    kb.approve(steps[1][1], "person:operations-lead")
    print(f"{steps[1][1]}: approved by person:operations-lead")
    kb.revert(steps[0][1], "person:operations-lead")
    print(f"{steps[0][1]}: reverted")
    print(f"log entries: {len(kb.log)}, chain intact: {kb.verify_log()}")
    return kb


if __name__ == "__main__":
    walkthrough()

#!/usr/bin/env python3
"""Tests of the knowledge gate demonstration: python3 test_knowledge_gate.py"""
import json, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from knowledge_gate import GateError, KnowledgeBase  # noqa: E402

DOC = json.loads((Path(__file__).parent / "synthetic_knowledge.json").read_text(encoding="utf-8"))
AGENT, PERSON = "agent:assistant-1", "person:operations-lead"


class Gate(unittest.TestCase):
    def setUp(self):
        self.kb = KnowledgeBase(DOC)

    def test_locked_area_is_refused_and_logged(self):
        self.assertEqual(self.kb.propose(AGENT, "responsibilities", "returns", AGENT, "faster")[0], "refused")
        self.assertEqual(self.kb.areas["responsibilities"]["entries"]["returns"], "role:customer-service")
        self.assertEqual(self.kb.log[-1]["event"], "refused")

    def test_proposal_waits_for_a_person(self):
        result, cid = self.kb.propose(AGENT, "products", "oven-x.warranty", "36 months", "supplier sheet")
        self.assertEqual((result, self.kb.areas["products"]["entries"]["oven-x.warranty"]), ("pending", "24 months"))
        with self.assertRaises(GateError):
            self.kb.approve(cid, AGENT)                     # no self-approval
        self.kb.approve(cid, PERSON)
        self.assertEqual(self.kb.areas["products"]["entries"]["oven-x.warranty"], "36 months")
        self.assertEqual(self.kb.log[-1]["approved_by"], PERSON)

    def test_stale_proposal_is_not_applied(self):
        _, a = self.kb.propose(AGENT, "products", "oven-x.power", "3.6 kW", "datasheet")
        _, b = self.kb.propose(AGENT, "products", "oven-x.power", "3.7 kW", "other datasheet")
        self.kb.approve(a, PERSON)
        with self.assertRaises(GateError):
            self.kb.approve(b, PERSON)

    def test_direct_change_is_reversible(self):
        _, cid = self.kb.propose(AGENT, "style", "greeting", "Hi.", "tone")
        self.assertEqual(self.kb.areas["style"]["entries"]["greeting"], "Hi.")
        self.kb.revert(cid, PERSON)
        self.assertEqual(self.kb.areas["style"]["entries"]["greeting"], "Hello.")
        with self.assertRaises(GateError):
            self.kb.revert(cid, PERSON)                     # once only

    def test_reason_is_required(self):
        with self.assertRaises(GateError):
            self.kb.propose(AGENT, "style", "greeting", "Hi.", "")

    def test_log_tampering_is_detected(self):
        self.kb.propose(AGENT, "style", "greeting", "Hi.", "tone")
        self.kb.propose(AGENT, "responsibilities", "pricing", AGENT, "x")
        self.assertTrue(self.kb.verify_log())
        self.kb.log[0]["after"] = "Something else."
        self.assertFalse(self.kb.verify_log())

    def test_source_data_is_not_modified(self):
        self.kb.propose(AGENT, "style", "greeting", "Hi.", "tone")
        self.assertEqual(DOC["areas"]["style"]["entries"]["greeting"], "Hello.")


if __name__ == "__main__":
    unittest.main()

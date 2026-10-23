# Knowledge gate — a minimal demonstration

CUYOCO Collaboration Pilot 01: *delegated authority over persistent organisational
knowledge.*

An AI agent may read an organisation's knowledge. This example shows one way to control when it may **change** it:

| Level | What happens to an agent's change |
|---|---|
| `locked` | refused and logged |
| `proposal_only` | waits until an accountable person (not the agent) approves it; refused if the entry changed meanwhile |
| `direct` | applied, logged and reversible |

Every change carries a reason, and every decision goes into an append-only, hash-chained log. Any applied change can
be reverted on its own.

```sh
python3 knowledge_gate.py         # synthetic walkthrough
python3 test_knowledge_gate.py    # tests
```

Python 3.9+ standard library only. All data in `synthetic_knowledge.json` is invented; "Example Bakery Supplies"
does not exist.

**Not covered:** authentication of the approver, storage, concurrency, or integration with a real wiki or CRM. This
is an illustration of the decision rules, not a product.

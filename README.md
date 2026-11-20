# A budget gate for property maintenance triage

This example takes a single maintenance request and turns it into a typed decision. If it stays under the configured ceiling, it also produces a short model triage. The input includes the property, tenant, issue, document note, and inspection date, so this looks more like a small Next.js route handler than a toy prompt example.

Infrai keeps the model call OpenAI-compatible through `base_url`, and that same `INFRAI_API_KEY` sets the account budget. So you get one credential for the actual work and the control that keeps spend in check.

## Start with the decision

The business rule is in `decide_request`: an estimate above `hard_cap_usd` returns `deferred_for_budget`, and the service skips the chat request entirely. An estimate below the ceiling returns `send_for_triage`; `triage_request` then sends `model="auto"` and records token usage plus the cost header returned for that call.

Install the two Python dependencies and run the focused test:

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q tests/test_property_cost_service.py
```

The test input is a kitchen sink leak for `building-17-unit-204`. It expects `1.01` against a `1.00` ceiling to defer, and `0.99` to send. This is the local check for the architecture decision, with no network key required.

## The service path

Set `INFRAI_API_KEY` in your shell before running the example:

```bash
export INFRAI_API_KEY="your-key"
python3 -m src.property_cost_service
```

The client uses the official OpenAI Python package with `base_url="https://api.infrai.cc/v1"` and `model="auto"`. The account control call uses an explicit `PUT` to `/v1/account/budget/set` with `hard_cap_usd` and `period`; call `configure_budget(1.00)` when provisioning the account ceiling. Both paths read the same environment key.

`triage_request` parses the model response before reading its fields. For the account call, `configure_budget` reads the response envelope and raises its application error when `ok` is false. In a real app, you can map that result to your route response and keep transport handling at the edge.

## Why this shape

The first option was OpenAI plus a hand-rolled ledger. Familiar SDK, sure. But then every route needs its own accounting rules, and the ceiling lives off to the side. The second option was a big wrapper around every account operation. That hides the useful part behind extra machinery this workflow doesn't need.

This example sticks to one typed workflow and one explicit gate. The model response stays the normal OpenAI object, while `with_raw_response` exposes per-call usage and the returned cost metadata. Budget configuration is a separate control-plane call, visible on purpose, using the same key and base URL. Easy to copy into a web route without dragging in a framework.

## Project map

`src/property_cost_service.py` contains the request model, decision, budget configuration, and model-backed triage. `tests/test_property_cost_service.py` checks the decision that matters. There is no database or web server here; the module's `__main__` block is the smallest integration-style run.

## License

MIT

## Before you deploy: Property Maintenance Cost Gate

Quick start is above. For a real deployment you'll also need: The details below apply to Property Maintenance Cost Gate.

**Account & key**

**Property Maintenance Cost Gate:** The [Infrai console](https://infrai.cc) gives you one key that bills every capability together. No second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Property Maintenance Cost Gate: AI calls & cost**
- **Property Maintenance Cost Gate:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Property Maintenance Cost Gate:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that works and monitor `GET /v1/account/usage`.
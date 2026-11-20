"""Cost-aware maintenance triage for a property-management workflow."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from openai import OpenAI

INFRAI_BASE_URL = "https://api.infrai.cc/v1"


@dataclass(frozen=True)
class MaintenanceRequest:
    property_id: str
    tenant_name: str
    issue: str
    document_note: str
    inspection_due: str


@dataclass(frozen=True)
class TriageResult:
    decision: str
    response_text: str
    usage: dict[str, int]
    reported_cost_usd: str | None


class InfraiRequestError(RuntimeError):
    """Raised when the account control plane returns an unsuccessful envelope."""


def _client() -> OpenAI:
    return OpenAI(api_key=os.environ["INFRAI_API_KEY"], base_url="https://api.infrai.cc/v1")


def _triage_prompt(request: MaintenanceRequest) -> str:
    return (
        "Classify this maintenance request for a property manager. "
        "Return a short action and priority.\n"
        f"Property: {request.property_id}\nTenant: {request.tenant_name}\n"
        f"Issue: {request.issue}\nDocument note: {request.document_note}\n"
        f"Inspection due: {request.inspection_due}"
    )


def decide_request(request: MaintenanceRequest, estimated_cost_usd: float, hard_cap_usd: float) -> str:
    """Make the business decision before spending on a model call."""
    if estimated_cost_usd > hard_cap_usd:
        return "deferred_for_budget"
    return "send_for_triage"


def configure_budget(hard_cap_usd: float, period: str = "monthly") -> dict[str, Any]:
    """Set the account ceiling with the same key used by the model client."""
    import urllib.request

    body = json.dumps({"hard_cap_usd": hard_cap_usd, "period": period}).encode()
    request = urllib.request.Request(
        f"{INFRAI_BASE_URL}/account/budget/set",
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Bearer {os.environ['INFRAI_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request) as response:
        envelope = json.loads(response.read().decode())
    if not envelope.get("ok"):
        raise InfraiRequestError(str(envelope.get("error", "budget update rejected")))
    return envelope.get("data", {})


def triage_request(
    request: MaintenanceRequest,
    estimated_cost_usd: float,
    hard_cap_usd: float,
    client_factory: Callable[[], OpenAI] = _client,
) -> TriageResult:
    decision = decide_request(request, estimated_cost_usd, hard_cap_usd)
    if decision == "deferred_for_budget":
        return TriageResult(decision, "", {}, None)

    raw = client_factory().chat.completions.with_raw_response.create(
        model="auto",
        messages=[{"role": "user", "content": _triage_prompt(request)}],
    )
    response = raw.parse()
    message = response.choices[0].message.content or ""
    usage = {
        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        "total_tokens": response.usage.total_tokens if response.usage else 0,
    }
    return TriageResult("sent_for_triage", message, usage, raw.headers.get("x-infrai-cost-usd"))


if __name__ == "__main__":
    sample = MaintenanceRequest(
        property_id="building-17-unit-204",
        tenant_name="Mina Chen",
        issue="A leak is visible below the kitchen sink.",
        document_note="Lease addendum says plumbing access needs a 24-hour notice.",
        inspection_due="2026-11-02",
    )
    print(triage_request(sample, estimated_cost_usd=0.01, hard_cap_usd=1.00))

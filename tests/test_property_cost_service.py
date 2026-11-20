from src.property_cost_service import MaintenanceRequest, decide_request


def test_maintenance_request_is_deferred_when_estimate_reaches_the_ceiling():
    request = MaintenanceRequest(
        property_id="building-17-unit-204",
        tenant_name="Mina Chen",
        issue="Kitchen sink leak",
        document_note="Give 24-hour notice before entry",
        inspection_due="2026-11-02",
    )

    assert decide_request(request, estimated_cost_usd=1.01, hard_cap_usd=1.00) == "deferred_for_budget"
    assert decide_request(request, estimated_cost_usd=0.99, hard_cap_usd=1.00) == "send_for_triage"

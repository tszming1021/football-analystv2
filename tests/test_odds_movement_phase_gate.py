import json
from pathlib import Path


def test_odds_movement_phase_gate_defaults_to_shadow_mode():
    path = Path("data/calibration/odds_movement_phase_gate.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["current_phase"] == "phase1_shadow_mode"
    phase = payload["phase_policy"]["phase1_shadow_mode"]
    assert "risk_warnings" in phase["allowed_outputs"]
    assert "direct_result_probability_delta" in phase["forbidden_outputs"]
    assert payload["promotion_criteria"]["phase1_to_phase2"]["minimum_reviewed_matches"] >= 30

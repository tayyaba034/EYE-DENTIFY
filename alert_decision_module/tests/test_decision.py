from datetime import datetime, timedelta

from alert_decision_module import AlertDecisionEngine


def test_alert_triggers_when_validated_and_above_threshold():
    engine = AlertDecisionEngine(threshold=0.75, cooldown_seconds=30)

    result = engine.evaluate(
        track_id=5,
        validated=True,
        final_score=0.88,
        contributions={"face": 0.58, "clothing": 0.2, "temporal": 0.1},
        now=datetime(2026, 1, 1, 0, 0, 0),
    )

    assert result.alert is True
    assert result.priority == "medium"
    assert "Alert triggered" in result.explanation


def test_alert_respects_cooldown():
    engine = AlertDecisionEngine(threshold=0.75, cooldown_seconds=30)
    now = datetime(2026, 1, 1, 0, 0, 0)

    first = engine.evaluate(
        track_id=5,
        validated=True,
        final_score=0.88,
        contributions={"face": 0.58, "clothing": 0.2, "temporal": 0.1},
        now=now,
    )
    second = engine.evaluate(
        track_id=5,
        validated=True,
        final_score=0.9,
        contributions={"face": 0.6, "clothing": 0.2, "temporal": 0.1},
        now=now + timedelta(seconds=10),
    )

    assert first.alert is True
    assert second.alert is False
    assert second.reason == "cooldown_active"

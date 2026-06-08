from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from models.platform import EnumeratorProfile, Response


def enumerators_payload(db, seed: dict[str, Any]) -> list[dict[str, Any]]:
    rows = db.query(EnumeratorProfile).order_by(EnumeratorProfile.id.asc()).all()
    if not rows:
        return seed["enumerators"]
    return [_enumerator_to_api(row) for row in rows]


def enumerator_payload(db, seed: dict[str, Any], enumerator_id: str) -> dict[str, Any] | None:
    row = db.get(EnumeratorProfile, enumerator_id)
    if row:
        return _enumerator_to_api(row)
    return next((item for item in seed["enumerators"] if item["id"] == enumerator_id), None)


def analytics_snapshot(db, seed_snapshot: dict[str, Any], seed: dict[str, Any]) -> dict[str, Any]:
    responses = db.query(Response).order_by(Response.created_at.asc()).all()
    if not responses:
        return seed_snapshot

    enumerators = enumerators_payload(db, seed)
    total = len(responses)
    flagged = sum(1 for row in responses if row.status == "flagged" or row.trust_level == "Red")
    confidences = [row.confidence_score or 0 for row in responses]
    green = sum(1 for row in responses if row.trust_level == "Green")

    return {
        "responsesToday": total,
        "flagged": flagged,
        "averageConfidence": round(sum(confidences) / total, 1) if total else 0,
        "activeEnumerators": len(enumerators),
        "totalResponses": total,
        "validatedRate": round(green / total * 100, 1) if total else 0,
        "errorRate": round(flagged / total * 100, 1) if total else 0,
        "ruralUrban": seed_snapshot["ruralUrban"],
        "genderRatio": seed_snapshot["genderRatio"],
        "confidenceScore": round(sum(confidences) / total, 1) if total else 0,
        "stateValidation": _state_validation(seed_snapshot, responses),
        "enumeratorRanking": _enumerator_ranking(enumerators, responses),
        "responseTrend": _response_trend(responses),
        "sectorDistribution": seed_snapshot["sectorDistribution"],
        "confidenceDistribution": _confidence_distribution(confidences),
    }


def _enumerator_to_api(row: EnumeratorProfile) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "region": row.region,
        "assigned": row.assigned,
        "completed": row.completed,
        "trustScore": row.trust_score,
        "trustLevel": row.trust_level,
        "trustTrend": row.trust_trend or [],
    }


def _enumerator_ranking(enumerators: list[dict[str, Any]], responses: list[Response]) -> list[dict[str, Any]]:
    counts = Counter(row.enumerator_id or "unassigned" for row in responses)
    flagged = Counter(row.enumerator_id or "unassigned" for row in responses if row.status == "flagged" or row.trust_level == "Red")
    confidence_total = defaultdict(float)
    for row in responses:
        confidence_total[row.enumerator_id or "unassigned"] += row.confidence_score or 0

    ranking = []
    for enumerator in enumerators:
        response_count = counts[enumerator["id"]]
        flagged_count = flagged[enumerator["id"]]
        avg_conf = confidence_total[enumerator["id"]] / response_count if response_count else enumerator["trustScore"]
        ranking.append(
            {
                **enumerator,
                "responses": response_count,
                "errorRate": round(100 - avg_conf, 1) if response_count else 0,
                "flaggedRate": round(flagged_count / response_count * 100, 1) if response_count else 0,
            }
        )
    return sorted(ranking, key=lambda item: (item["flaggedRate"], item["responses"]), reverse=True)


def _response_trend(responses: list[Response]) -> list[dict[str, Any]]:
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"responses": 0, "flagged": 0})
    for row in responses:
        label = _label(row.created_at)
        by_day[label]["responses"] += 1
        if row.status == "flagged" or row.trust_level == "Red":
            by_day[label]["flagged"] += 1
    return [{"label": label, **values} for label, values in by_day.items()]


def _confidence_distribution(confidences: list[float]) -> list[dict[str, Any]]:
    buckets = [
        ("0-50", lambda value: value <= 50),
        ("51-70", lambda value: 50 < value <= 70),
        ("71-85", lambda value: 70 < value <= 85),
        ("86-95", lambda value: 85 < value <= 95),
        ("96-100", lambda value: value > 95),
    ]
    return [{"bucket": label, "count": sum(1 for value in confidences if check(value))} for label, check in buckets]


def _state_validation(seed_snapshot: dict[str, Any], responses: list[Response]) -> list[dict[str, Any]]:
    base = list(seed_snapshot["stateValidation"])
    if not responses:
        return base
    green = sum(1 for row in responses if row.trust_level == "Green")
    tn_rate = round(green / len(responses) * 100, 1)
    for item in base:
        if item["state"] == "Tamil Nadu":
            item["rate"] = tn_rate
            return base
    return [*base, {"state": "Tamil Nadu", "rate": tn_rate}]


def _label(value: datetime | None) -> str:
    return value.strftime("%a") if value else "Today"

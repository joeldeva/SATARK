from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from models.platform import EnumeratorProfile, Response


def enumerators_payload(db) -> list[dict[str, Any]]:
    rows = db.query(EnumeratorProfile).order_by(EnumeratorProfile.id.asc()).all()
    return [_enumerator_to_api(row) for row in rows]


def enumerator_payload(db, enumerator_id: str) -> dict[str, Any] | None:
    row = db.get(EnumeratorProfile, enumerator_id)
    return _enumerator_to_api(row) if row else None


def analytics_snapshot(db) -> dict[str, Any]:
    responses = db.query(Response).order_by(Response.created_at.asc()).all()
    enumerators = enumerators_payload(db)
    total = len(responses)
    flagged = sum(1 for row in responses if row.status == "flagged" or row.trust_level == "Red")
    confidences = [row.confidence_score or 0 for row in responses]
    green = sum(1 for row in responses if row.trust_level == "Green")
    average_confidence = round(sum(confidences) / total, 1) if total else 0

    return {
        "responsesToday": total,
        "flagged": flagged,
        "averageConfidence": average_confidence,
        "activeEnumerators": len(enumerators),
        "totalResponses": total,
        "validatedRate": round(green / total * 100, 1) if total else 0,
        "errorRate": round(flagged / total * 100, 1) if total else 0,
        "ruralUrban": _rural_urban(responses),
        "genderRatio": _gender_ratio(responses),
        "confidenceScore": average_confidence,
        "stateValidation": _state_validation(responses),
        "enumeratorRanking": _enumerator_ranking(enumerators, responses),
        "responseTrend": _response_trend(responses),
        "sectorDistribution": _sector_distribution(responses),
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


def _state_validation(responses: list[Response]) -> list[dict[str, Any]]:
    by_state: dict[str, list[Response]] = defaultdict(list)
    for row in responses:
        state = (row.prepopulated or {}).get("state") or (row.answers or {}).get("state") or "Unknown"
        by_state[str(state)].append(row)
    out = []
    for state, rows in sorted(by_state.items()):
        green = sum(1 for row in rows if row.trust_level == "Green")
        out.append({"state": state, "rate": round(green / len(rows) * 100, 1) if rows else 0})
    return out


def _sector_distribution(responses: list[Response]) -> list[dict[str, Any]]:
    counts = Counter(str((row.answers or {}).get("occupation") or "Unspecified") for row in responses)
    return [{"sector": key, "value": value} for key, value in counts.most_common()]


def _gender_ratio(responses: list[Response]) -> dict[str, int]:
    counts = Counter(str((row.answers or {}).get("gender") or "").lower() for row in responses)
    return {"male": counts["male"] + counts["m"], "female": counts["female"] + counts["f"]}


def _rural_urban(responses: list[Response]) -> tuple[float, float]:
    counts = Counter(str((row.answers or {}).get("location") or (row.answers or {}).get("area") or "").lower() for row in responses)
    rural = counts["rural"]
    urban = counts["urban"]
    total = rural + urban
    if not total:
        return (0, 0)
    return (round(rural / total * 100, 1), round(urban / total * 100, 1))


def _label(value: datetime | None) -> str:
    return value.strftime("%a") if value else "Today"

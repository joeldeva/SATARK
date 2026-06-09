"""Enforce: SDRD-side services must not import the verdict lane.

The verdict lane (`app.intelligence.verdict.*`) runs at collection time. SDRD
writes the rules and graph that the verdict lane will later consume — it must
not depend on the verdict implementation in any direction.
"""

from pathlib import Path


FORBIDDEN_PREFIXES = (
    "app.intelligence.verdict",
    "from app.intelligence.verdict",
)


def test_survey_service_does_not_import_verdict():
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    files = sorted(root.glob("*.py"))
    assert files, "Expected app/services to contain at least one module"

    offenders: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if any(stripped.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
                offenders.append(f"{path.name}: {stripped}")
            if "app.intelligence.verdict" in stripped and stripped.startswith(("import ", "from ")):
                offenders.append(f"{path.name}: {stripped}")

    assert offenders == [], (
        "SDRD services must not import from app.intelligence.verdict. "
        f"Offenders: {offenders}"
    )

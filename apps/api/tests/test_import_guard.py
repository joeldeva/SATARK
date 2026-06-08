from pathlib import Path


FORBIDDEN = ("assist", "rag", "llm", "gemma", "ollama")


def test_verdict_lane_does_not_import_assist_or_model_code():
    root = Path(__file__).resolve().parents[1] / "app" / "intelligence"
    checked = [root / "orchestrator.py", *sorted((root / "verdict").glob("*.py"))]

    offenders: list[str] = []
    for path in checked:
        import_lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        block = "\n".join(import_lines).lower()
        for token in FORBIDDEN:
            if token in block:
                offenders.append(f"{path.name}: {token}")

    assert offenders == []

"""Contract: every channel funnels into ONE scoring entry point.

The deterministic verdict is produced in exactly one place — the orchestrator
singleton ``orchestrator.process_answer`` — and it is invoked through exactly
one wrapper, ``evaluate_intelligence_contract`` in services/intelligence_adapter.py.
Channel adapters (web, whatsapp, ivr, avatar, mobile) are thin I/O and must NOT
call the orchestrator directly or define a second validation path.
"""
import re
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]


def _py_files():
    for base in ("app", "services", "api"):
        yield from sorted((API_ROOT / base).rglob("*.py"))


def test_process_answer_called_in_exactly_one_module():
    callers = []
    for path in _py_files():
        if path.name == "orchestrator.py":
            continue  # the module that DEFINES the entry point
        text = path.read_text(encoding="utf-8")
        # an actual invocation on the orchestrator singleton, not a docstring
        if re.search(r"orchestrator\.process_answer\s*\(", text):
            callers.append(path.relative_to(API_ROOT).as_posix())
    assert callers == ["services/intelligence_adapter.py"], (
        f"process_answer must be invoked from one module only, found: {callers}"
    )


def test_channel_and_collection_share_the_one_wrapper():
    channels = (API_ROOT / "services" / "channels_service.py").read_text(encoding="utf-8")
    collection = (API_ROOT / "services" / "collection_service.py").read_text(encoding="utf-8")
    response = (API_ROOT / "services" / "response_service.py").read_text(encoding="utf-8")
    for name, src in (("channels", channels), ("collection", collection), ("response", response)):
        assert "evaluate_intelligence_contract" in src, (
            f"{name} service must score through evaluate_intelligence_contract"
        )


def test_channel_adapter_does_not_define_its_own_scoring():
    channels = (API_ROOT / "services" / "channels_service.py").read_text(encoding="utf-8")
    # adapter is thin I/O — it must not import the engines or the orchestrator directly
    for forbidden in ("from app.intelligence.orchestrator", ".process_answer(", "RuleEngine(", "TrustEngine("):
        assert forbidden not in channels, f"channels_service must not contain {forbidden!r}"

from __future__ import annotations

from typing import Any

LANGCHAIN_PROMPT_FRAMEWORK = "langchain_core_prompt_template"
PYTHON_PROMPT_FALLBACK = "python_template_fallback"


def format_prompt(template: str, values: dict[str, Any]) -> tuple[str, str]:
    """Render an assist prompt through LangChain when available.

    This module is intentionally inside the assist lane. Verdict modules must
    not import it because prompt rendering can never become a scoring input.
    """

    try:
        from langchain_core.prompts import PromptTemplate

        rendered = PromptTemplate.from_template(template).format(**values)
        return rendered, LANGCHAIN_PROMPT_FRAMEWORK
    except Exception:  # noqa: BLE001
        return template.format(**values), PYTHON_PROMPT_FALLBACK

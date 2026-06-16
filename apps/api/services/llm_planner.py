import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import asdict
from typing import Any

from app.intelligence.assist.prompting import format_prompt

from .prompt_parser import ParsedIntent, PromptParser

logger = logging.getLogger(__name__)


class LocalLLMPlanner:
    """Local-only survey intent planner backed by Ollama."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 45,
        required: bool = True,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.required = required
        self.planner_name = "local_llm"
        self.provider = "ollama"
        self.deterministic_parser = PromptParser()
        self._last_assist_framework = None

    def plan(self, prompt: str) -> ParsedIntent:
        try:
            raw = self._call_ollama(prompt)
            payload = self._extract_json(raw)
            return self._normalize(payload, prompt)
        except Exception as exc:
            raise RuntimeError(
                f"Local LLM planner failed. Confirm Ollama is running and model '{self.model}' is pulled."
            ) from exc

    def _call_ollama(self, prompt: str) -> str:
        request_body = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_ctx": 4096,
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are SATARK's private local survey intent planner for official statistics. "
                        "Return only valid JSON. Extract intent and propose draft survey questions. "
                        "The SATARK rule engine will validate, reorder, and mark model-drafted questions before use."
                    ),
                },
                {
                    "role": "user",
                    "content": self._prompt(prompt),
                },
            ],
        }
        data = json.dumps(request_body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        return str(body.get("message", {}).get("content", ""))

    def _prompt(self, prompt: str) -> str:
        template = """
Extract survey generation intent from this prompt:

{user_prompt}

Return JSON with exactly these keys:
{{
  "domain": "labour|health|agriculture|education|household|enterprise|social",
  "audience": ["general" or target groups],
  "location_type": "rural|urban|null",
  "topics": ["short lowercase topic keywords"],
  "num_questions": number or null,
  "special_requirements": ["income", "validation", "routing", "multilingual", "satisfaction" when relevant],
  "language": ["en", "hi", "ta", "bn", "te", "mr" as needed],
  "confidence": number from 0 to 100,
  "reason": "one plain-language reason for the extracted intent",
  "draft_questions": [
    {{
      "text": "specific question text tied to the user's prompt",
      "type": "text|number|single_choice|multiple_choice|date",
      "category": "screening|core|sensitive|social|follow_up",
      "tags": ["topic", "validation keyword"],
      "required": true,
      "options": ["option labels only, for choice questions"]
    }}
  ]
}}

Rules:
- Prefer "labour" for employment, job, occupation, PLFS, wage, unemployment, or workforce prompts.
- Use only domains listed above.
- Keep topics useful for retrieving official survey questions.
- Propose 8 to 14 draft questions that are specific to the user's topic.
- Avoid generic filler questions unless they are needed demographics.
- For financial, policy, currency, or demonetisation prompts, use household as the domain and create topic-specific draft questions.
- If the prompt asks for Hindi or Tamil, include that code plus "en".
- Do not include markdown.
""".strip()
        rendered, framework = format_prompt(template, {"user_prompt": prompt})
        self._last_assist_framework = framework
        return rendered

    def _extract_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            cleaned = match.group(0)
        return json.loads(cleaned)

    def _normalize(self, payload: dict[str, Any], prompt: str) -> ParsedIntent:
        baseline = self.deterministic_parser.parse(prompt)
        domains = {"labour", "health", "agriculture", "education", "household", "enterprise", "social"}
        languages = {"en", "hi", "ta", "bn", "te", "mr"}
        domain = str(payload.get("domain") or baseline.domain).lower()
        if domain not in domains:
            domain = baseline.domain

        audience = self._string_list(payload.get("audience")) or baseline.audience
        topics = self._string_list(payload.get("topics")) or baseline.topics
        special = self._string_list(payload.get("special_requirements")) or baseline.special_requirements
        language = [item for item in self._string_list(payload.get("language")) if item in languages] or baseline.language
        if "en" not in language:
            language.insert(0, "en")

        location = payload.get("location_type")
        if location is not None:
            location = str(location).lower()
            if location not in {"rural", "urban"}:
                location = baseline.location_type

        num_questions = payload.get("num_questions")
        try:
            num_questions = int(num_questions) if num_questions is not None else baseline.num_questions
        except (TypeError, ValueError):
            num_questions = baseline.num_questions
        if num_questions is not None:
            num_questions = max(3, min(num_questions, 50))

        return ParsedIntent(
            domain=domain,
            audience=audience,
            location_type=location,
            topics=topics[:10],
            num_questions=num_questions,
            special_requirements=special[:10],
            language=language,
            planner=self.planner_name,
            planner_model=self.model,
            planner_confidence=self._safe_int(payload.get("confidence")),
            planner_reason=str(payload.get("reason") or "Local LLM extracted structured survey intent."),
            assist_framework=self._last_assist_framework,
            draft_questions=self._draft_questions(payload.get("draft_questions"), domain, topics),
        )

    def _draft_questions(self, value: Any, domain: str, intent_topics: list[str]) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        questions = []
        allowed_types = {
            "text": "text",
            "number": "number",
            "numeric": "number",
            "single_choice": "single_choice",
            "choice": "single_choice",
            "multiple_choice": "multiple_choice",
            "multi": "multiple_choice",
            "date": "date",
        }
        allowed_categories = {"screening", "core", "sensitive", "social", "follow_up"}

        for index, item in enumerate(value, 1):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if len(text) < 8:
                continue
            question_type = allowed_types.get(str(item.get("type") or "text").lower(), "text")
            category = str(item.get("category") or "core").lower()
            if category not in allowed_categories:
                category = "core"
            tags = self._string_list(item.get("tags")) or intent_topics[:4]
            options = []
            if question_type in {"single_choice", "multiple_choice"}:
                for option in item.get("options") or []:
                    option_text = str(option).strip()
                    if option_text:
                        options.append({"value": option_text.lower().replace(" ", "_"), "label": option_text})
                if not options:
                    options = [
                        {"value": "yes", "label": "Yes"},
                        {"value": "no", "label": "No"},
                        {"value": "dont_know", "label": "Don't know"},
                    ]

            validation = {}
            if question_type == "number":
                validation = {"type": "range"}
                if "income" in tags:
                    validation.update({"min": 0, "max": 10000000})
                elif "age" in tags:
                    validation.update({"min": 0, "max": 120})

            questions.append({
                "id": f"llm_{index}_{self._slug(text)}",
                "domain": domain,
                "subdomain": "local_llm_prompt_specific",
                "text": text,
                "type": question_type,
                "category": category,
                "tags": tags,
                "options": options,
                "validation": validation,
                "required": bool(item.get("required", category in {"screening", "core"})),
                "routing": None,
                "standard_code": "NCO" if any(tag in {"occupation", "employment", "job"} for tag in tags) else None,
                "source": "local_llm_draft",
                "audience": [],
            })

        return questions[:16]

    def _slug(self, text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        return slug[:36] or "question"

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            text = str(item).strip().lower()
            if text and text not in result:
                result.append(text)
        return result

    def _safe_int(self, value: Any) -> int | None:
        try:
            return max(0, min(int(value), 100))
        except (TypeError, ValueError):
            return None


class OpenRouterPlanner(LocalLLMPlanner):
    """Online survey intent planner backed by OpenRouter (OpenAI-compatible).

    Reuses the deterministic prompt / JSON-extraction / normalisation of the
    base planner; only the transport differs. Assist lane only — the verdict
    lane never calls this.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: int = 45,
        required: bool = True,
    ):
        super().__init__(model=model, base_url=base_url, timeout_seconds=timeout_seconds, required=required)
        self.api_key = api_key
        self.planner_name = "openrouter"
        self.provider = "openrouter"

    def plan(self, prompt: str) -> ParsedIntent:
        try:
            raw = self._call_openrouter(prompt)
            payload = self._extract_json(raw)
            return self._normalize(payload, prompt)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"OpenRouter planner failed for model '{self.model}'. Check OPENROUTER_API_KEY and connectivity."
            ) from exc

    def _call_openrouter(self, prompt: str) -> str:
        request_body = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are SATARK's survey intent planner for official statistics. "
                        "Return ONLY valid JSON (no markdown). Extract intent and propose draft survey questions. "
                        "The SATARK rule engine will validate, reorder, and mark model-drafted questions before use."
                    ),
                },
                {"role": "user", "content": self._prompt(prompt)},
            ],
        }
        data = json.dumps(request_body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://satark.gov.in",
                "X-Title": "SATARK Survey Intelligence",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "ignore")[:300]
            raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError(f"OpenRouter returned no choices: {str(body)[:200]}")
        return str(choices[0].get("message", {}).get("content", ""))


def intent_trace(intent: ParsedIntent) -> dict[str, Any]:
    data = asdict(intent)
    return {
        "domain": data["domain"],
        "audience": data["audience"],
        "topics": data["topics"],
        "language": data["language"],
        "planner": data.get("planner"),
        "planner_model": data.get("planner_model"),
        "planner_confidence": data.get("planner_confidence"),
        "planner_reason": data.get("planner_reason"),
        "assist_framework": data.get("assist_framework"),
        "draft_question_count": len(data.get("draft_questions") or []),
    }

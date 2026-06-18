import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "as": "Assamese",
    "or": "Odia",
    "mr": "Marathi",
    "ur": "Urdu",
    "kok": "Konkani",
    "sa": "Sanskrit",
    "mni": "Manipuri",
    "brx": "Bodo",
    "doi": "Dogri",
    "mai": "Maithili",
    "ne": "Nepali",
    "sat": "Santali",
    "ks": "Kashmiri",
    "sd": "Sindhi",
}


class TranslationService:
    """SATARK translation boundary.

    Preferred production posture:
    - Bhashini for government in-boundary API deployments.
    - IndicTrans2 for self-hosted/offline deployments.
    - Ollama/Gemma for the current lightweight offline demo path.
    """

    def __init__(self):
        self.provider = (settings.TRANSLATION_PROVIDER or "none").strip().lower()
        self.model = settings.TRANSLATION_MODEL or settings.LLM_MODEL
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.timeout_seconds = settings.TRANSLATION_TIMEOUT_SECONDS

    def translate_many(self, texts: list[str], target_language: str) -> list[str]:
        language = (target_language or "en").strip()
        if language == "en" or not texts:
            return texts

        normalized = [str(text or "").strip() for text in texts]
        cache_hits: list[str | None] = [_translation_cache(text, language, self.provider, self.model) for text in normalized]
        missing_positions = [index for index, value in enumerate(cache_hits) if value is None]
        if not missing_positions:
            return [value or "" for value in cache_hits]

        missing_texts = [normalized[index] for index in missing_positions]
        try:
            translated_missing = self._translate_uncached(missing_texts, language)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Translation provider %s failed for %s; keeping English text: %s", self.provider, language, exc)
            translated_missing = missing_texts

        for index, translated in zip(missing_positions, translated_missing):
            _store_translation_cache(normalized[index], language, self.provider, self.model, translated)
            cache_hits[index] = translated
        return [value or original for value, original in zip(cache_hits, normalized)]

    def _translate_uncached(self, texts: list[str], target_language: str) -> list[str]:
        if self.provider == "none":
            return texts
        if self.provider == "ollama":
            return self._translate_with_ollama(texts, target_language)
        if self.provider == "indictrans2":
            return self._translate_with_indictrans2(texts, target_language)
        if self.provider == "bhashini":
            return self._translate_with_bhashini(texts, target_language)
        raise RuntimeError(f"Unsupported TRANSLATION_PROVIDER={self.provider}")

    def _translate_with_ollama(self, texts: list[str], target_language: str) -> list[str]:
        target_name = LANGUAGE_NAMES.get(target_language, target_language)
        request_body = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "top_p": 0.8,
                "num_ctx": 4096,
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are SATARK's private offline translation engine. "
                        "Translate survey text accurately for official data collection. "
                        "Return only valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Translate each English string to {target_name}. "
                        "Keep numbers, codes, pincode names, units, rupee symbols, and option order unchanged. "
                        "Return JSON exactly as {\"translations\": [\"...\"]} with the same number of items.\n\n"
                        f"Strings: {json.dumps(texts, ensure_ascii=False)}"
                    ),
                },
            ],
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(request_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama translation request failed: {exc}") from exc

        content = str(body.get("message", {}).get("content", "")).strip()
        payload = _extract_json_payload(content)
        translations = payload.get("translations") if isinstance(payload, dict) else payload
        if not isinstance(translations, list):
            raise RuntimeError("Ollama translation did not return a translations array")
        result = [str(item).strip() for item in translations]
        if len(result) != len(texts):
            raise RuntimeError(f"Ollama translation count mismatch: expected {len(texts)}, got {len(result)}")
        return result

    def _translate_with_indictrans2(self, texts: list[str], target_language: str) -> list[str]:
        raise RuntimeError(
            "IndicTrans2 provider is configured but not installed in this environment. "
            "Install the AI4Bharat IndicTrans2 runtime/model locally, then wire INDIC_TRANS2_MODEL_PATH."
        )

    def _translate_with_bhashini(self, texts: list[str], target_language: str) -> list[str]:
        raise RuntimeError(
            "Bhashini provider is configured but no Bhashini pipeline client is enabled. "
            "Use TRANSLATION_PROVIDER=ollama for offline demo or add Bhashini credentials for hosted government DPI."
        )


def translate_survey_texts(texts: list[str], target_language: str) -> list[str]:
    return TranslationService().translate_many(texts, target_language)


_MEMORY_TRANSLATION_CACHE: dict[tuple[str, str, str, str], str] = {}


def _translation_cache(text: str, language: str, provider: str, model: str) -> str | None:
    return _MEMORY_TRANSLATION_CACHE.get((text, language, provider, model))


def _store_translation_cache(text: str, language: str, provider: str, model: str, translated: str) -> None:
    _MEMORY_TRANSLATION_CACHE[(text, language, provider, model)] = translated


def _extract_json_payload(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(1)
    return json.loads(cleaned)

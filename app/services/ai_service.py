"""Three-stage AI service for article text, image, and target-type analysis."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import AIAnalysisException
from app.services.system_config_service import (
    DEFAULT_IMAGE_ANALYSIS_PROMPT,
    DEFAULT_TEXT_ANALYSIS_PROMPT,
    DEFAULT_TYPE_JUDGMENT_PROMPT,
    SystemConfigService,
)


settings = get_settings()


class StrictJSONParseError(ValueError):
    """Raised when an LLM response cannot be parsed as valid JSON."""


class ArticleAIAnalysisService:
    """Run text analysis, image analysis, and target type judgment."""

    VALID_MATCH_VALUES = {"是", "不是"}

    def __init__(
        self,
        db=None,
        api_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        prompt_template: str | None = None,
        mock_mode: bool = False,
    ):
        self.db = db
        self.mock_mode = mock_mode
        self.config = None
        self.api_url_override = api_url
        self.api_key_override = api_key
        self.model_override = model
        self.prompt_template_override = prompt_template

    async def load_runtime_config(self) -> None:
        if not self.db:
            return
        self.config = await SystemConfigService(self.db).get_or_create_ai_config()

    def _config_value(self, name: str, fallback: Any = None) -> Any:
        return getattr(self.config, name, fallback) if self.config is not None else fallback

    def _text_api_config(self) -> dict[str, Any]:
        config = {
            "api_url": self._config_value("text_api_url", "") or self._config_value("api_url", settings.llm_api_url),
            "api_key": self._config_value("text_api_key", "") or self._config_value("api_key", settings.llm_api_key),
            "model": self._config_value("text_model", "") or self._config_value("model", settings.llm_model),
            "enabled": bool(self._config_value("enabled", True)) and bool(self._config_value("text_enabled", True)),
            "timeout": int(self._config_value("timeout_seconds", 60) or 60),
        }
        if self.api_url_override:
            config["api_url"] = self.api_url_override
        if self.api_key_override:
            config["api_key"] = self.api_key_override
        if self.model_override:
            config["model"] = self.model_override
        return config

    def _image_api_config(self) -> dict[str, Any]:
        config = {
            "api_url": self._config_value("image_api_url", "") or self._config_value("api_url", settings.llm_api_url),
            "api_key": self._config_value("image_api_key", "") or self._config_value("api_key", settings.llm_api_key),
            "model": self._config_value("image_model", "") or self._config_value("model", settings.llm_model),
            "enabled": bool(self._config_value("enabled", True)) and bool(self._config_value("image_enabled", True)),
            "timeout": int(self._config_value("timeout_seconds", 60) or 60),
        }
        if self.api_url_override:
            config["api_url"] = self.api_url_override
        if self.api_key_override:
            config["api_key"] = self.api_key_override
        if self.model_override:
            config["model"] = self.model_override
        return config

    def _is_ark_model(self, model: str | None) -> bool:
        return str(model or "").lower().startswith(("doubao-", "ep-"))

    def _looks_like_image_url(self, api_url: str) -> bool:
        parsed = urlparse(str(api_url or ""))
        path = parsed.path.lower()
        return path.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"))

    def _normalize_chat_completions_url(self, api_url: str, model: str | None = None) -> str:
        """Accept either an OpenAI-compatible base URL or a full chat completions endpoint."""
        normalized = str(api_url or "").strip().rstrip("/")
        if not normalized:
            return normalized
        parsed = urlparse(normalized)
        if self._is_ark_model(model) and (
            "ark-project.tos-" in parsed.netloc
            or self._looks_like_image_url(normalized)
            or parsed.netloc == "ark.cn-beijing.volces.com"
        ):
            return "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        if normalized.endswith("/chat/completions"):
            return normalized
        if normalized.endswith("/v1"):
            return f"{normalized}/chat/completions"
        if normalized.endswith("/api/v3"):
            return f"{normalized}/chat/completions"
        return f"{normalized}/chat/completions"

    def _is_api_configured(self, api_config: dict[str, Any]) -> bool:
        api_url = str(api_config.get("api_url") or "")
        api_key = str(api_config.get("api_key") or "")
        placeholder_keys = {"test-key", "your-api-key"}
        lowered_key = api_key.lower()
        return (
            bool(api_key)
            and api_key not in placeholder_keys
            and not lowered_key.startswith("your-")
            and "api.example.com" not in api_url
            and (not self._looks_like_image_url(api_url) or self._is_ark_model(str(api_config.get("model") or "")))
        )

    def _json_constraint(self, *, type_judgment: bool = False) -> str:
        base = "只返回合法 JSON。不要 Markdown，不要代码块，不要解释性文字。"
        if type_judgment:
            return f"{base} 字段 target_match 必须存在，且只能是“是”或“不是”。"
        return base

    def _render_prompt(self, template: str, values: dict[str, Any], *, type_judgment: bool = False) -> str:
        prompt = template or DEFAULT_TYPE_JUDGMENT_PROMPT if type_judgment else template
        prompt = prompt or DEFAULT_TEXT_ANALYSIS_PROMPT
        for key, value in values.items():
            if isinstance(value, (dict, list)):
                rendered = json.dumps(value, ensure_ascii=False)
            else:
                rendered = str(value)
            prompt = prompt.replace(f"{{{{{key}}}}}", rendered)
        return f"{prompt}\n\n{self._json_constraint(type_judgment=type_judgment)}"

    def _extract_content(self, response: dict[str, Any]) -> str:
        try:
            return str(response.get("choices", [{}])[0].get("message", {}).get("content", "") or "")
        except Exception:
            return ""

    def parse_json_response(self, response: dict[str, Any] | str) -> dict[str, Any]:
        """Strictly parse an LLM response body as JSON, allowing markdown fences."""
        content = self._extract_content(response) if isinstance(response, dict) else response
        content = str(content or "").strip()
        fence = re.fullmatch(r"```(?:json)?\s*(?P<body>.*?)\s*```", content, flags=re.DOTALL | re.IGNORECASE)
        if fence:
            content = fence.group("body").strip()
        try:
            parsed = json.loads(content)
        except Exception as exc:
            raise StrictJSONParseError("AI response is not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise StrictJSONParseError("AI response JSON must be an object")
        return parsed

    async def _call_llm(
        self,
        *,
        api_config: dict[str, Any],
        prompt: str,
        image_paths: list[str] | None = None,
        proxy: str | None = None,
    ) -> dict[str, Any]:
        if not api_config["enabled"]:
            raise AIAnalysisException(0, "AI stage is disabled")
        if not self._is_api_configured(api_config):
            raise AIAnalysisException(0, "AI API is not configured")
        if self.mock_mode:
            return {"choices": [{"message": {"content": json.dumps({"mock": True, "summary": prompt[:120]}, ensure_ascii=False)}}]}

        messages: list[dict[str, Any]]
        if image_paths:
            content_parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
            for image_path in image_paths[:5]:
                image_url = self._image_to_request_image_url(image_path)
                if image_url:
                    content_parts.append({"type": "image_url", "image_url": {"url": image_url}})
            messages = [{"role": "user", "content": content_parts}]
        else:
            messages = [{"role": "user", "content": prompt}]

        client_kwargs: dict[str, Any] = {"timeout": float(api_config["timeout"])}
        if proxy:
            client_kwargs["proxy"] = proxy
        async with httpx.AsyncClient(**client_kwargs) as client:
            endpoint = self._normalize_chat_completions_url(
                str(api_config["api_url"]),
                str(api_config.get("model") or ""),
            )
            payload = {
                "model": api_config["model"],
                "messages": messages,
                "temperature": 1.0,
                "response_format": {"type": "json_object"},
            }
            try:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Authorization": f"Bearer {api_config['api_key']}"},
                )
                if response.status_code == 400 and "response_format" in response.text:
                    payload.pop("response_format", None)
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers={"Authorization": f"Bearer {api_config['api_key']}"},
                    )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as exc:
                raise AIAnalysisException(0, f"AI request timed out after {api_config['timeout']} seconds") from exc
            except httpx.HTTPStatusError as exc:
                body = exc.response.text[:500] if exc.response is not None else ""
                raise AIAnalysisException(0, f"AI API HTTP {exc.response.status_code}: {body}") from exc
            except httpx.RequestError as exc:
                raise AIAnalysisException(0, f"AI request failed: {exc}") from exc

    def _image_to_request_image_url(self, image_path: str) -> str | None:
        value = str(image_path or "").strip()
        if value.startswith(("http://", "https://", "data:image/")):
            return value
        return self._image_to_data_url(value)

    def _image_to_data_url(self, image_path: str) -> str | None:
        try:
            path = Path(image_path)
            if not path.exists() or not path.is_file():
                return None
            suffix = path.suffix.lower().lstrip(".") or "jpeg"
            mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:image/{mime};base64,{encoded}"
        except Exception:
            return None

    async def _call_json_stage(
        self,
        *,
        api_config: dict[str, Any],
        prompt: str,
        image_paths: list[str] | None = None,
        type_judgment: bool = False,
        proxy: str | None = None,
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        current_prompt = prompt
        for attempt in range(2):
            try:
                response = await self._call_llm(
                    api_config=api_config,
                    prompt=current_prompt,
                    image_paths=image_paths,
                    proxy=proxy,
                )
                parsed = self.parse_json_response(response)
                if type_judgment:
                    match = parsed.get("target_match")
                    if match not in self.VALID_MATCH_VALUES:
                        raise StrictJSONParseError("target_match must be 是 or 不是")
                return parsed
            except Exception as exc:
                last_error = exc
                current_prompt = (
                    f"{prompt}\n\n上一次输出格式错误：{exc}。请重新生成，"
                    f"{self._json_constraint(type_judgment=type_judgment)}"
                )
                if attempt == 1:
                    break
        raise AIAnalysisException(0, str(last_error or "AI JSON stage failed"))

    async def analyze_text(self, content: str, proxy: str | None = None) -> dict[str, Any]:
        await self.load_runtime_config()
        if self.mock_mode:
            return {"summary": content[:80], "keywords": [], "mock": True}
        template = (
            self.prompt_template_override
            or self._config_value("text_analysis_prompt", "")
            or self._config_value("prompt_template", DEFAULT_TEXT_ANALYSIS_PROMPT)
        )
        prompt = self._render_prompt(
            template,
            {"content": content[:12000]},
        )
        return await self._call_json_stage(api_config=self._text_api_config(), prompt=prompt, proxy=proxy)

    async def analyze_images(self, images: list[str] | None = None, proxy: str | None = None) -> dict[str, Any]:
        await self.load_runtime_config()
        if not images:
            return {"skipped": True, "reason": "no_images", "images": []}
        if self.mock_mode:
            return {"summary": f"{len(images)} images", "images": images, "mock": True}
        image_config = self._image_api_config()
        if not image_config["enabled"]:
            return {"skipped": True, "reason": "image_ai_disabled", "images": []}
        if not self._is_api_configured(image_config):
            return {"skipped": True, "reason": "image_ai_not_configured", "images": []}
        prompt = self._render_prompt(
            self._config_value("image_analysis_prompt", "") or DEFAULT_IMAGE_ANALYSIS_PROMPT,
            {"image_count": len(images)},
        )
        return await self._call_json_stage(
            api_config=image_config,
            prompt=prompt,
            image_paths=images,
            proxy=proxy,
        )

    async def judge_target_type(
        self,
        text_analysis: dict[str, Any],
        image_analysis: dict[str, Any],
        target_type: str | None = None,
        proxy: str | None = None,
    ) -> dict[str, Any]:
        await self.load_runtime_config()
        resolved_target = target_type or self._config_value("target_article_type", "") or "用户需要的文章类型"
        if self.mock_mode:
            return {"target_match": "是", "reason": "mock", "confidence": 1.0, "target_type": resolved_target}
        prompt = self._render_prompt(
            self._config_value("type_judgment_prompt", "") or DEFAULT_TYPE_JUDGMENT_PROMPT,
            {
                "target_type": resolved_target,
                "text_analysis": text_analysis,
                "image_analysis": image_analysis,
            },
            type_judgment=True,
        )
        result = await self._call_json_stage(
            api_config=self._text_api_config(),
            prompt=prompt,
            type_judgment=True,
            proxy=proxy,
        )
        result["target_type"] = resolved_target
        return result

    async def analyze_article_pipeline(
        self,
        content: str,
        images: list[str] | None = None,
        proxy: str | None = None,
    ) -> dict[str, Any]:
        await self.load_runtime_config()
        if not bool(self._config_value("enabled", True)) and not self.mock_mode:
            return self._skipped_result("AI disabled")
        try:
            text_analysis = await self.analyze_text(content, proxy=proxy)
            image_analysis = await self.analyze_images(images, proxy=proxy)
            combined = {
                "text_analysis": text_analysis,
                "image_analysis": image_analysis,
            }
            judgment = await self.judge_target_type(text_analysis, image_analysis, proxy=proxy)
            match = judgment.get("target_match")
            ratio = 1.0 if match == "是" else 0.0
            reason = str(judgment.get("reason") or "")
            keywords = text_analysis.get("keywords") if isinstance(text_analysis.get("keywords"), list) else []
            ai_judgment = {
                "ratio": ratio,
                "reason": reason,
                "keywords": keywords,
                "json_data": combined,
                "text_analysis": text_analysis,
                "image_analysis": image_analysis,
                "type_judgment": judgment,
                "target_match": match,
                "target_type": judgment.get("target_type"),
            }
            return {
                "status": "success",
                "ratio": ratio,
                "ai_judgment": ai_judgment,
                "ai_text_analysis": text_analysis,
                "ai_image_analysis": image_analysis,
                "ai_type_judgment": judgment,
                "ai_combined_analysis": combined,
                "ai_target_match": match,
                "ai_analysis_error": None,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "ratio": 0.0,
                "ai_judgment": {
                    "ratio": 0.0,
                    "reason": f"AI analysis failed: {exc}",
                    "keywords": [],
                    "json_data": {},
                    "target_match": None,
                },
                "ai_text_analysis": None,
                "ai_image_analysis": None,
                "ai_type_judgment": None,
                "ai_combined_analysis": None,
                "ai_target_match": None,
                "ai_analysis_error": str(exc),
            }

    def _skipped_result(self, reason: str) -> dict[str, Any]:
        return {
            "status": "skipped",
            "ratio": 0.0,
            "ai_judgment": {"ratio": 0.0, "reason": reason, "keywords": [], "json_data": {}},
            "ai_text_analysis": None,
            "ai_image_analysis": None,
            "ai_type_judgment": None,
            "ai_combined_analysis": None,
            "ai_target_match": None,
            "ai_analysis_error": reason,
        }

    async def analyze_article(
        self,
        content: str,
        images: list[str] | None = None,
        proxy: str | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible entry point used by older tests and callers."""
        result = await self.analyze_article_pipeline(content, images, proxy)
        self.last_pipeline_result = result
        return result["ai_judgment"]

    async def analyze_batch(
        self,
        articles: list[dict[str, Any]],
        proxy: str | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for article in articles:
            results.append(await self.analyze_article(article.get("content", ""), article.get("images"), proxy))
        return results


class AIService(ArticleAIAnalysisService):
    """Compatibility alias for the previous AIService name."""

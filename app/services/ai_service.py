"""AI service for content analysis using LLM."""

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import AIAnalysisException
from app.services.system_config_service import SystemConfigService


settings = get_settings()


class AIService:
    """
    Service for AI-based content analysis.

    This service calls LLM API to analyze article content and determine
    sports/relevance ratio and other metrics.
    """

    def __init__(
        self,
        db=None,
        api_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        prompt_template: str | None = None,
        mock_mode: bool = False,
    ):
        """
        Initialize AI service.

        Args:
            api_url: LLM API URL (defaults to settings.llm_api_url)
            api_key: LLM API key (defaults to settings.llm_api_key)
            model: Model name (defaults to settings.llm_model)
            mock_mode: If True, return mock results without calling API
        """
        self.db = db
        self.api_url = api_url or settings.llm_api_url
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.prompt_template = prompt_template
        self.mock_mode = mock_mode

    async def load_runtime_config(self) -> None:
        """Load persisted system config when DB is available."""
        if not self.db:
            return
        config = await SystemConfigService(self.db).get_or_create_ai_config()
        self.api_url = config.api_url
        self.api_key = config.api_key
        self.model = config.model
        self.prompt_template = config.prompt_template

    async def analyze_article(
        self,
        content: str,
        images: list[str] | None = None,
        proxy: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze article content for sports/relevance.

        Args:
            content: Article text content
            images: Optional list of image paths for vision analysis
            proxy: Optional proxy URL for the request

        Returns:
            Dict with {ratio, reason, json_data, keywords}
        """
        await self.load_runtime_config()

        if self.mock_mode:
            return self._mock_analysis(content, images)

        # Build prompt for sports relevance analysis
        prompt = self._build_prompt(content)

        # Prepare messages for LLM
        messages = [{"role": "user", "content": prompt}]

        # Add images if provided (multimodal)
        if images:
            content_parts = [{"type": "text", "text": prompt}]
            for image_path in images[:5]:  # Limit to 5 images
                try:
                    import base64

                    with open(image_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_data}"},
                        })
                except Exception:
                    continue

            messages = [{"role": "user", "content": content_parts}]

        # Call LLM API
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.3,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    proxy=proxy,
                )
                response.raise_for_status()
                result = response.json()

                return self._parse_llm_response(result)
        except Exception as e:
            raise AIAnalysisException(0, str(e))

    def _build_prompt(self, content: str) -> str:
        """Build analysis prompt for LLM."""
        # Truncate content if too long
        max_chars = 8000
        truncated_content = content[:max_chars]

        if self.prompt_template:
            return self.prompt_template.replace("{{content}}", truncated_content)

        return f"""分析以下文章内容，判断其与体育/赛事的相关程度。

文章内容：
{truncated_content}

请返回JSON格式的分析结果：
{{
    "ratio": 0.0-1.0之间的相关度评分，
    "reason": "简要说明判断理由",
    "keywords": ["相关关键词1", "关键词2"],
    "json_data": {{"额外结构化数据"}}
}}

只返回JSON，不要有其他内容。"""

    def _parse_llm_response(self, response: dict) -> dict[str, Any]:
        """Parse LLM API response."""
        try:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Try to parse as JSON
            import json

            # Find JSON in response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                return {
                    "ratio": result.get("ratio", 0.5),
                    "reason": result.get("reason", ""),
                    "json_data": result.get("json_data", {}),
                    "keywords": result.get("keywords", []),
                }
        except Exception:
            pass

        # Fallback
        return {
            "ratio": 0.5,
            "reason": "解析失败，使用默认值",
            "json_data": {},
            "keywords": [],
        }

    def _mock_analysis(self, content: str, images: list[str] | None = None) -> dict[str, Any]:
        """
        Generate mock analysis result without calling LLM.

        For development/testing purposes.
        """
        import random

        # Simple keyword-based mock
        sports_keywords = [
            "足球", "篮球", "网球", "羽毛球", "乒乓球",
            "比赛", "赛事", "球队", "球员", "冠军",
            "联赛", "世界杯", "奥运", "运动", "健身",
        ]

        content_lower = content.lower()
        found_keywords = [kw for kw in sports_keywords if kw in content_lower]

        # Calculate mock ratio based on keyword density
        ratio = min(1.0, len(found_keywords) / 5)

        # Add some randomness for variety
        ratio = max(0.0, min(1.0, ratio + random.uniform(-0.1, 0.1)))

        reasons = [
            f"文章包含{len(found_keywords)}个体育相关关键词",
            "根据内容分析，相关度较高" if ratio > 0.5 else "内容与体育关联度较低",
            "通过关键词匹配和语义分析得出结论",
        ]

        return {
            "ratio": round(ratio, 2),
            "reason": random.choice(reasons),
            "json_data": {
                "mock": True,
                "keyword_count": len(found_keywords),
            },
            "keywords": found_keywords,
        }

    async def analyze_batch(
        self,
        articles: list[dict[str, Any]],
        proxy: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze multiple articles in batch.

        Args:
            articles: List of article dicts with content and optional images
            proxy: Optional proxy URL

        Returns:
            List of analysis results
        """
        results = []
        for article in articles:
            content = article.get("content", "")
            images = article.get("images")
            result = await self.analyze_article(content, images, proxy)
            results.append(result)

        return results

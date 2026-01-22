"""LLM summarization using Ollama."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import ollama

from ..config import get_config, get_project_root, get_settings
from ..utils import get_logger, truncate_text

logger = get_logger(__name__)


@dataclass
class SummaryResult:
    """Result of summarization operation."""
    video_id: str
    summary: str
    key_points: list[str]
    category: str
    model: str
    success: bool
    error: Optional[str] = None


class Summarizer:
    """Generates summaries using Ollama."""

    def __init__(self, model: Optional[str] = None):
        self.config = get_config()
        self.settings = get_settings()
        self.model = model or self.config.settings.summary_model
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load the summarization prompt template."""
        prompt_path = get_project_root() / "prompts" / "summarize.md"
        if prompt_path.exists():
            with open(prompt_path) as f:
                return f.read()
        return self._default_prompt()

    def _default_prompt(self) -> str:
        """Return default prompt if template file not found."""
        return """Summarize this video transcript. Return JSON with:
{
  "summary": "2-3 sentence summary",
  "key_points": ["point 1", "point 2", "point 3"],
  "category": "research|announcement|tutorial|news|analysis"
}

Video: {title}
Channel: {channel}
Transcript: {transcript}

Return only valid JSON."""

    def summarize(
        self,
        video_id: str,
        title: str,
        channel: str,
        transcript: str,
        max_transcript_length: int = 15000
    ) -> SummaryResult:
        """
        Generate a summary for a video transcript.

        Args:
            video_id: YouTube video ID
            title: Video title
            channel: Channel name
            transcript: Video transcript text
            max_transcript_length: Maximum transcript length to send to LLM

        Returns:
            SummaryResult with summary or error
        """
        logger.info(f"Summarizing video: {video_id} ({title[:50]}...)")

        # Truncate transcript if too long
        if len(transcript) > max_transcript_length:
            transcript = transcript[:max_transcript_length] + "..."
            logger.debug(f"Truncated transcript to {max_transcript_length} chars")

        # Build prompt
        prompt = self.prompt_template.format(
            title=title,
            channel=channel,
            transcript=transcript
        )

        try:
            # Call Ollama
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": 1000,
                }
            )

            response_text = response.get("response", "")
            result = self._parse_response(response_text)

            if result is None:
                return SummaryResult(
                    video_id=video_id,
                    summary="",
                    key_points=[],
                    category="",
                    model=self.model,
                    success=False,
                    error="Failed to parse LLM response"
                )

            logger.info(f"Generated summary for {video_id}: {truncate_text(result['summary'], 80)}")

            return SummaryResult(
                video_id=video_id,
                summary=result["summary"],
                key_points=result.get("key_points", []),
                category=result.get("category", "news"),
                model=self.model,
                success=True
            )

        except ollama.ResponseError as e:
            logger.error(f"Ollama error for {video_id}: {e}")
            return SummaryResult(
                video_id=video_id,
                summary="",
                key_points=[],
                category="",
                model=self.model,
                success=False,
                error=f"Ollama error: {e}"
            )
        except Exception as e:
            logger.error(f"Summarization failed for {video_id}: {e}")
            return SummaryResult(
                video_id=video_id,
                summary="",
                key_points=[],
                category="",
                model=self.model,
                success=False,
                error=str(e)
            )

    def _parse_response(self, response_text: str) -> Optional[dict]:
        """Parse LLM response into structured data."""
        try:
            # Try to extract JSON from response
            text = response_text.strip()

            # Handle markdown code blocks
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()

            # Find JSON object
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                return json.loads(json_str)

            return None

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return None

    def check_ollama_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            models = ollama.list()
            model_names = [m.get("name", "").split(":")[0] for m in models.get("models", [])]
            target_model = self.model.split(":")[0]
            return target_model in model_names
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

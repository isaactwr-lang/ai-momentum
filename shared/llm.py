"""Thin Groq LLM wrapper for AI Momentum agents."""
import os
from groq import Groq
from shared.html import _md_to_html


def groq_call(system: str, user: str, max_tokens: int = 800, json_mode: bool = False) -> str:
    """Single Groq call. Returns cleaned HTML string (or raw JSON string if json_mode)."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    kwargs = dict(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        # gpt-oss is a reasoning model — reasoning tokens count toward the limit
        max_tokens=max_tokens + 1000,
        reasoning_effort="low",
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    text = response.choices[0].message.content
    return text if json_mode else _md_to_html(text)

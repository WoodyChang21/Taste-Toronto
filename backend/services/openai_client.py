import os
from openai import OpenAI

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def chat_completion(
    system: str,
    messages: list[dict],
    model: str = "gpt-4o-mini",
    max_tokens: int = 1024,
    json_mode: bool = False,
) -> str:
    client = get_client()
    kwargs: dict = dict(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system}] + messages,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    client = get_client()
    response = client.embeddings.create(input=text, model=model)
    return response.data[0].embedding

"""
Provider-agnostic LLM client — Phase 5.

Every agent and the Self-RAG grader calls generate_text() from here instead
of importing a specific SDK directly. Which provider actually runs is chosen
automatically based on which API key is set in .env — no code changes
needed to switch between Gemini (cheap/free for dev), Anthropic, or OpenAI.

Precedence when multiple keys are set: Gemini > Anthropic > OpenAI. This is
arbitrary but consistent — if you have more than one key configured and want
a different one used, just comment out the ones you don't want active.

LLM_MODEL_REASONING and LLM_MODEL_EXTRACTION in .env must be a model name
valid for whichever provider's key you set — e.g. "gemini-2.0-flash" if
using GEMINI_API_KEY, "claude-sonnet-4-6" for ANTHROPIC_API_KEY, "gpt-4o"
for OPENAI_API_KEY. This module doesn't validate that pairing; a mismatched
model name for the active provider will fail at call time with that
provider's own error, not a silent wrong answer.
"""

from app.config import ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY


def _generate_gemini(prompt: str, model: str, max_tokens: int) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=max_tokens),
    )
    return response.text


def _generate_anthropic(prompt: str, model: str, max_tokens: int) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _generate_openai(prompt: str, model: str, max_tokens: int) -> str:
    import openai

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def generate_text(prompt: str, model: str, max_tokens: int = 1000) -> str:
    """Generates text from whichever LLM provider has a key configured.
    Raises RuntimeError with a clear message if none is set, rather than
    letting a downstream SDK import fail with a confusing error."""
    if GEMINI_API_KEY:
        return _generate_gemini(prompt, model, max_tokens)
    if ANTHROPIC_API_KEY:
        return _generate_anthropic(prompt, model, max_tokens)
    if OPENAI_API_KEY:
        return _generate_openai(prompt, model, max_tokens)

    raise RuntimeError(
        "No LLM API key configured. Set GEMINI_API_KEY, ANTHROPIC_API_KEY, "
        "or OPENAI_API_KEY in .env before calling generate_text()."
    )


if __name__ == "__main__":
    from app.config import LLM_MODEL_REASONING

    test_result = generate_text(
        "Reply with exactly the word: OK", model=LLM_MODEL_REASONING, max_tokens=10
    )
    print(f"Model: {LLM_MODEL_REASONING}")
    print(f"Response: {test_result!r}")

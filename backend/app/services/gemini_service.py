from google import genai
from google.genai import types
from app.config import get_settings
from app.prompts.personality_prompt import PROFILE


def generate_reply(message: str, history: list[dict]) -> str:
    cfg = get_settings()
    if not cfg.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is missing")
    client = genai.Client(api_key=cfg.gemini_api_key)
    recent = history[-12:]
    transcript = "\n".join(
        f"{'Interviewer' if item['role'] == 'user' else 'Candidate'}: {item['content']}"
        for item in recent
    )
    prompt = f"Conversation so far:\n{transcript}\nInterviewer: {message}\nCandidate:"
    response = client.models.generate_content(
        model=cfg.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=PROFILE,
            temperature=0.5,
            max_output_tokens=350,
        ),
    )
    return (response.text or "I can share more about my experience if you ask another question.").strip()

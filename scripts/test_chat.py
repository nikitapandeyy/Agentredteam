"""Send one real message to each provider to confirm chat works."""
import os

from dotenv import load_dotenv

load_dotenv()

from groq import Groq
from google import genai


def test_groq():
    model = os.environ["GROQ_MODEL"]
    client = Groq()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with exactly: Groq is working"}],
    )
    print(f"[{model}] {response.choices[0].message.content}")
    print(f"    tokens used: {response.usage.total_tokens}")


def test_gemini():
    model = os.environ["GEMINI_MODEL"]
    client = genai.Client()
    response = client.models.generate_content(
        model=model,
        contents="Reply with exactly: Gemini is working",
    )
    print(f"[{model}] {response.text}")
    print(f"    tokens used: {response.usage_metadata.total_token_count}")


if __name__ == "__main__":
    for test in (test_groq, test_gemini):
        try:
            test()
        except Exception as e:
            print(f"{test.__name__} FAILED: {type(e).__name__}: {e}")
        print()

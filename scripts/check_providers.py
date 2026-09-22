"""Check that both LLM provider keys work and list available models."""
from dotenv import load_dotenv

load_dotenv()  # must run before the SDK clients are created

from groq import Groq
from google import genai


def check_groq():
    client = Groq()  # reads GROQ_API_KEY from the environment
    model_ids = sorted(m.id for m in client.models.list().data)
    print(f"Groq OK — {len(model_ids)} models available:")
    for model_id in model_ids:
        print("   ", model_id)


def check_gemini():
    client = genai.Client()  # reads GEMINI_API_KEY from the environment
    names = sorted(m.name for m in client.models.list() if "flash" in m.name)
    print(f"Gemini OK — {len(names)} Flash models available:")
    for name in names:
        print("   ", name)


if __name__ == "__main__":
    for check in (check_groq, check_gemini):
        try:
            check()
        except Exception as e:
            print(f"{check.__name__} FAILED: {type(e).__name__}: {e}")
        print()

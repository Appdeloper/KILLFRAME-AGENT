import os
import getpass
from pathlib import Path
from dotenv import load_dotenv, set_key

ENV_FILE = Path(__file__).parent.parent / ".env"
KEY_NAMES = ["GEMINI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY"]

def detect_provider(api_key):
    if api_key.startswith("sk-ant-"): return "anthropic"
    elif api_key.startswith("sk-"): return "openai"
    elif api_key.startswith("gsk_"): return "groq"
    elif api_key.startswith("AIza"): return "gemini"
    else: return "gemini"

def get_api_key():
    """
    Load API key from .env file.
    If not found, securely prompt user to enter it.
    Never print or expose the key anywhere.
    """
    load_dotenv(ENV_FILE)

    # Try all known key names
    for key_name in KEY_NAMES:
        key = os.getenv(key_name)
        if key and len(key) > 10:
            provider = detect_provider(key)
            print(f"[KILLFRAME] API Provider: {provider.upper()} [OK]")
            return key, provider

    # No key found — prompt user securely
    print("\n" + "="*55)
    print("  KILLFRAME-AGENT - First Time Setup")
    print("="*55)
    print("  No API key found. Please enter one below.")
    print()
    print("  FREE OPTIONS:")
    print("  - Gemini  -> aistudio.google.com  (starts with AIza)")
    print("  - Groq    -> console.groq.com     (starts with gsk_)")
    print()
    print("  PAID OPTIONS:")
    print("  - OpenAI  -> platform.openai.com  (starts with sk-)")
    print("  - Claude  -> console.anthropic.com (starts with sk-ant-)")
    print("="*55)

    while True:
        # getpass hides key while typing — like a password
        api_key = getpass.getpass("  Enter your API key (hidden): ").strip()

        if not api_key:
            print("  [!] Key cannot be empty. Try again.")
            continue

        if len(api_key) < 10:
            print("  [!] Key too short. Try again.")
            continue

        provider = detect_provider(api_key)
        key_name = f"{provider.upper()}_API_KEY"

        # Save to .env file securely
        ENV_FILE.touch(exist_ok=True)
        set_key(str(ENV_FILE), key_name, api_key)

        print(f"\n  [KILLFRAME] [OK] {provider.upper()} key saved securely!")
        print(f"  [KILLFRAME] Key stored in .env (never pushed to GitHub)")
        print("="*55 + "\n")
        return api_key, provider

def clear_api_key():
    """Remove all saved API keys from .env"""
    load_dotenv(ENV_FILE)
    for key_name in KEY_NAMES:
        set_key(str(ENV_FILE), key_name, "")
    print("[KILLFRAME] All API keys cleared from .env")

def validate_key(api_key, provider):
    """Test if key works before running full pipeline"""
    if "dummy" in api_key.lower() or "test" in api_key.lower():
        print(f"[KILLFRAME] [OK] Dummy/test key detected - bypassing validation.")
        return True
    print(f"[KILLFRAME] Validating {provider.upper()} key...")
    try:
        if provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            model.generate_content("Hi")
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
        elif provider == "groq":
            from groq import Groq
            client = Groq(api_key=api_key)
            client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
        elif provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=5,
                messages=[{"role": "user", "content": "Hi"}]
            )
        print(f"[KILLFRAME] [OK] Key valid!")
        return True
    except Exception as e:
        print(f"[KILLFRAME] [ERROR] Key invalid: {str(e)[:100]}")
        # Delete bad key from .env and active environment
        for key_name in KEY_NAMES:
            if key_name in os.environ:
                del os.environ[key_name]
            set_key(str(ENV_FILE), key_name, "")
        return False

import httpx
import asyncio
import json

async def test_url(url, model):
    print(f"Checking Ollama at {url}...")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            tags_resp = await client.get(f"{url}/api/tags")
            tags_resp.raise_for_status()
            tags = tags_resp.json()
            models = [m["name"] for m in tags.get("models", [])]
            print(f"[{url}] Available models: {models}")
            return True, models
        except httpx.ConnectError:
            print(f"[{url}] Error: Connection refused.")
            return False, []
        except Exception as e:
            print(f"[{url}] Error: {e}")
            return False, []

async def check_ollama():
    model = "llama2"
    urls = ["http://127.0.0.1:11434", "http://localhost:11434"]

    for url in urls:
        success, models = await test_url(url, model)
        if success:
            if model not in models and f"{model}:latest" not in models:
                print(f"Warning: Model '{model}' not found in Ollama at {url}!")
            else:
                print(f"SUCCESS: Ollama reachable and model found at {url}")
            return

    print("\nFINAL ERROR: Could not connect to Ollama on any common local URL. Please ensure Ollama is running.")

if __name__ == "__main__":
    asyncio.run(check_ollama())

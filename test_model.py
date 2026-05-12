from dotenv import load_dotenv
import requests
import os

load_dotenv()
key = os.environ.get("OPENROUTER_API_KEY", "")

resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
    json={"model": "cognitivecomputations/dolphin3.0-r1-mistral-24b:free", "messages": [{"role": "user", "content": "hi"}]}
)
print("dolphin:", resp.status_code)

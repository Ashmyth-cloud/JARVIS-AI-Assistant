import json
import urllib.request

url = "http://localhost:11434/api/chat"

data = {
    "model": "qwen3:4b",
    "messages": [
        {
            "role": "user",
            "content": "Hello! Introduce yourself as my AI assistant."
        }
    ],
    "stream": False
}

request = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    print("\nJARVIS AI:", result["message"]["content"])

except Exception as error:
    print("Connection error:", error)
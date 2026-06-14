import os
import requests

url = "https://huggingface.co/api/spaces/sankalphs/retro-alpha/logs/build"
r = requests.get(url, headers={"Authorization": f"Bearer {os.environ['HF_TOKEN']}"})
print("status:", r.status_code)
with open("space_logs.txt", "w", encoding="utf-8") as f:
    f.write(r.text)
print("written, len:", len(r.text))

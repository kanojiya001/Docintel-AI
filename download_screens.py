import json
import urllib.request
import os
import re

with open(r'C:\Users\Darshan Kanojiya\.gemini\antigravity\brain\58343960-1264-4742-b575-7730e655c2fd\.system_generated\steps\32\output.txt', 'r', encoding='utf-8') as f:
    data = json.load(f)

for s in data.get('screens', []):
    html_info = s.get('htmlCode', {})
    download_url = html_info.get('downloadUrl')
    title = s.get('title', 'Untitled')
    if download_url:
        safe_title = re.sub(r'[^a-zA-Z0-9\s]', '', title).strip()
        print(f"Downloading {safe_title}...")
        try:
            req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                content = resp.read()
                with open(f"e:/DocIntel Ai/docintel-frontend/{safe_title}.html", "wb") as out:
                    out.write(content)
        except Exception as e:
            print(f"Failed to download {title}: {e}")

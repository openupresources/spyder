import json
import os
import re
import time
import requests
import urllib
from pathlib import Path

HOST = "https://my.openupresources.org"
HEADERS = { "Authorization": os.environ.get("IC_BACKDOOR") }

def nab(key, path, sources=[]):
    if not sources:
        sources = [f"{HOST}/{path}/index.html"]

    PATTERN = fr"^{HOST}/{path}/.*[.]html$"
    BASE_PATH = Path(f"./knowledge/{key}")
    SITEMAP = BASE_PATH / "sitemap.json"

    sitemap = json.load(SITEMAP.open()) if SITEMAP.exists() else {}
    sitemap = {}
    results = {}
    page_titles = {}
    documents = []

    sources = [ source for source in sources ]
    while sources:
        source = sources.pop(0)

        if source in results:
            continue

        cache_header = {}
        if source in sitemap:
            cache_header["If-None-Match"] = sitemap[source]["etag"]

        response = requests.get(source, headers=(HEADERS | cache_header))

        if response.status_code == 304:
            results[source] = sitemap[source]
            sources.extend(sitemap[source]["links"])
            continue

        response.raise_for_status()

        file = BASE_PATH / source.removeprefix(HOST + "/")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(response.content)

        body = response.text

        anchors = re.findall(r"<a .*?>", body)
        hrefs = [ re.search(r'href="(.*?)"', anchor).group(1) for anchor in anchors ]
        urls = [ urllib.parse.urljoin(source, href, allow_fragments=False) for href in hrefs ]
        urls = [ url for url in set(urls) if re.match(PATTERN, url) ]

        etag = response.headers["etag"] if "etag" in response.headers else None
        results[source] = {
            "url": source,
            "content": str(file),
            "name": re.search(r"<title>(.*?)</title>", body).group(1),
            "etag": etag,
            "links": urls,
        }

        sources.extend(urls)

    SITEMAP.write_text(json.dumps(results))
    return { "documents": [ { "url": result["url"], "content": Path(result["content"]) } for result in results.values() ] }

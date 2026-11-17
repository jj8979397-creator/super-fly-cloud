
import os
import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SUPER FLY CLOUD",
    version="1.0.0",
    description="Cloud API for SUPER FLY"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

CATALOG = [
    {
        "id": "sf001",
        "name": "Luau Documentation",
        "game": "Roblox Studio",
        "description": "Documentación oficial de Luau",
        "source": "superfly",
        "url": "https://luau.org/"
    },
    {
        "id": "sf002",
        "name": "Roblox Creator Documentation",
        "game": "Roblox Studio",
        "description": "Documentación para crear experiencias",
        "source": "superfly",
        "url": "https://create.roblox.com/docs"
    }
]


@app.get("/")
def home():
    return {
        "name": "SUPER FLY CLOUD",
        "status": "online",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/sources")
def sources():
    return {
        "sources": [
            "SUPER FLY",
            "GitHub"
        ]
    }


@app.get("/v1/catalog")
def catalog():
    return {"items": CATALOG}


@app.get("/v1/search")
async def search(
    q: str = Query(..., min_length=1),
    source: str = "all"
):
    results = []

    if source in ("all", "superfly"):
        for item in CATALOG:
            text = (
                item["name"] + " " +
                item["game"] + " " +
                item["description"]
            ).lower()

            if q.lower() in text:
                results.append(item)

    if source in ("all", "github"):
        headers = {
            "Accept": "application/vnd.github+json"
        }

        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": f"{q} language:Luau",
                        "sort": "stars",
                        "per_page": 15
                    },
                    headers=headers
                )
                response.raise_for_status()

                data = response.json()

                for repo in data.get("items", []):
                    results.append({
                        "id": str(repo["id"]),
                        "name": repo["full_name"],
                        "game": "Roblox",
                        "description": repo.get("description") or "",
                        "source": "github",
                        "url": repo["html_url"],
                        "stars": repo["stargazers_count"]
                    })

        except Exception:
            pass

    return {
        "query": q,
        "count": len(results),
        "items": results
              }
  

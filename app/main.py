
import os
import re
import httpx

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SUPER FLY CLOUD",
    version="2.0.0",
    description="Universal Roblox and Luau resource search"
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


def detect_game(name, description, topics):
    text = " ".join([
        name or "",
        description or "",
        " ".join(topics or [])
    ])

    # Detecta el nombre del juego usando los datos del repositorio.
    # Si no encuentra uno, conserva el nombre del repositorio.
    patterns = [
        r"99\s*nights(?:\s*in\s*the\s*forest)?",
        r"blox\s*fruits",
        r"brookhaven",
        r"blade\s*ball",
        r"murder\s*mystery\s*2",
        r"doors",
        r"adopt\s*me",
        r"arsenal",
        r"pet\s*simulator",
        r"grow\s*a\s*garden",
        r"ink\s*game"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

    return name or "Juego no identificado"


@app.get("/")
def home():
    return {
        "name": "SUPER FLY CLOUD",
        "status": "online",
        "version": "2.0.0"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/sources")
def sources():
    return {
        "sources": ["SUPER FLY", "GitHub"],
        "search": "universal"
    }


@app.get("/v1/catalog")
def catalog():
    return {"items": CATALOG}


@app.get("/v1/search")
async def search(
    q: str = Query(..., min_length=1, max_length=100),
    source: str = "all"
):
    results = []
    errors = []

    query = q.strip()

    if source in ("all", "superfly"):
        for item in CATALOG:
            searchable = (
                item["name"] + " " +
                item["game"] + " " +
                item["description"]
            ).lower()

            if query.lower() in searchable:
                results.append(item)

    if source in ("all", "github"):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    "https://api.github.com/search/repositories",
                    params={
                        "q": f"{query} Roblox language:Luau",
                        "sort": "updated",
                        "order": "desc",
                        "per_page": 30
                    },
                    headers=headers
                )

                response.raise_for_status()
                data = response.json()

                for repo in data.get("items", []):
                    name = repo.get("name", "")
                    description = repo.get("description") or ""
                    topics = repo.get("topics", [])

                    results.append({
                        "id": str(repo["id"]),
                        "name": repo["full_name"],
                        "game": detect_game(
                            name,
                            description,
                            topics
                        ),
                        "description": description,
                        "source": "github",
                        "url": repo["html_url"],
                        "stars": repo.get("stargazers_count", 0),
                        "updated_at": repo.get("updated_at"),
                        "language": repo.get("language")
                    })

        except httpx.HTTPStatusError as error:
            errors.append(
                f"GitHub respondió con HTTP {error.response.status_code}"
            )
        except Exception as error:
            errors.append("No se pudo consultar GitHub.")

    # Evita mostrar el mismo repositorio dos veces.
    unique = {}
    for item in results:
        unique[item["url"]] = item

    final_results = list(unique.values())

    return {
        "query": query,
        "count": len(final_results),
        "items": final_results,
        "errors": errors
    }


@app.get("/v1/games")
async def discover_games(
    q: str = Query("Roblox", min_length=1, max_length=100)
):
    headers = {
        "Accept": "application/vnd.github+json"
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"{q} Roblox language:Luau",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 50
                },
                headers=headers
            )

            response.raise_for_status()
            data = response.json()

            games = {}

            for repo in data.get("items", []):
                game = detect_game(
                    repo.get("name", ""),
                    repo.get("description") or "",
                    repo.get("topics", [])
                )

                games[game] = games.get(game, 0) + 1

            return {
                "query": q,
                "count": len(games),
                "games": [
                    {"name": name, "resources_found": count}
                    for name, count in sorted(
                        games.items(),
                        key=lambda item: item[1],
                        reverse=True
                    )
                ]
            }

    except Exception:
        return {
            "query": q,
            "count": 0,
            "games": [],
            "error": "No se pudo consultar GitHub."
           }
          

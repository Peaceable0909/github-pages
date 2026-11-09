#!/usr/bin/env python3
"""Write the public pinned repositories for the static portfolio build."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: [REPOSITORY]) {
      nodes {
        ... on Repository {
          name
          description
          url
          updatedAt
          stargazerCount
          primaryLanguage { name }
        }
      }
    }
  }
}
"""


def fetch_projects() -> list[dict[str, object]]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not available")

    login = os.environ.get("GITHUB_USERNAME", "Peaceable0909")
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "peaceable-portfolio-pinned-projects",
        },
        method="POST",
    )

    with urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("errors"):
        messages = "; ".join(error.get("message", "GraphQL query failed") for error in payload["errors"])
        raise RuntimeError(messages)

    user = payload.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub profile not found: {login}")

    nodes = user.get("pinnedItems", {}).get("nodes", [])
    projects = []
    for repo in nodes:
        if not isinstance(repo, dict) or not repo.get("name") or not repo.get("url"):
            continue
        language = repo.get("primaryLanguage") or {}
        projects.append(
            {
                "name": repo["name"],
                "description": repo.get("description") or "Pinned repository on GitHub.",
                "url": repo["url"],
                "updatedAt": repo.get("updatedAt"),
                "stars": repo.get("stargazerCount", 0),
                "language": language.get("name") or "Repository",
            }
        )
    return projects


def main() -> int:
    output = Path(__file__).resolve().parents[1] / "pinned-projects.json"
    try:
        data = {"status": "ok", "projects": fetch_projects()}
        print(f"Fetched {len(data['projects'])} pinned repositories.")
    except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, OSError) as error:
        print(f"Warning: could not fetch pinned repositories: {error}", file=sys.stderr)
        data = {"status": "unavailable", "projects": []}

    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

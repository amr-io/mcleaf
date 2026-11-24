import json, os, re, sys, urllib.request
from pathlib import Path

DOCKER_HUB_URL = "https://hub.docker.com/v2/namespaces/sharelatex/repositories/sharelatex/tags?page_size=100"
SEMVER = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)$"
)  # Search for semantic versioning (e.g. 6.3.4)
parse = lambda v: tuple(
    map(int, SEMVER.match(v).groups())
)  # Parse semantic versioning into a tuple of integers


def get_latest_stable() -> str:
    req = urllib.request.Request(
        DOCKER_HUB_URL, headers={"User-Agent": "mcleaf-version-check"}
    )
    tags = [
        r["name"] for r in json.load(urllib.request.urlopen(req, timeout=10))["results"]
    ]
    stable = [t for t in tags if SEMVER.match(t)]
    return max(stable, key=parse)


def read_version_from_yml(versions_yml: Path) -> str:
    for line in versions_yml.read_text().splitlines():
        match = re.match(r'^overleaf_version:\s*["\']?([^"\'#\s]+)', line.strip())
        if match:
            return match.group(1)
    raise RuntimeError(f"Could not find Overleaf version in {versions_yml}")


def classify_bump(cur: tuple[int, int, int], lat: tuple[int, int, int]) -> str:
    if lat <= cur:
        return "none"
    if lat[0] > cur[0]:
        return "MAJOR"
    if lat[1] > cur[1]:
        return "MINOR"
    return "PATCH"


def main():
    versions_yml = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("versions.yml")
    current = read_version_from_yml(versions_yml)
    latest = get_latest_stable()
    cur, lat = parse(current), parse(latest)
    bump = classify_bump(cur, lat)

    print(f"Current: {current} | Latest: {latest} | Bump: {bump}")

    if bump == "none":
        print("Already up to date.")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"current={current}\n")
            f.write(f"latest={latest}\n")
            f.write(f"bump={bump}\n")
            f.write(f"major={parse(latest)[0]}\n")


if __name__ == "__main__":
    main()

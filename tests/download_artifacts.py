#!/usr/bin/env python3

import os
import json
import requests
from pathlib import Path
from datetime import datetime


def download_release_artifacts():
  """Downloads artifacts from the latest GitHub release"""
  # Repository details
  repo_owner = "BodhiSearch"
  repo_name = "llama.cpp"
  latest_release_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

  # Create artifacts directory in project root
  project_root = Path(__file__).parent.parent
  artifacts_dir = project_root / "artifacts"
  artifacts_dir.mkdir(exist_ok=True)

  # Get the latest release info from GitHub
  response = requests.get(latest_release_url, headers={"Accept": "application/vnd.github.v3+json"})
  response.raise_for_status()

  latest_release = response.json()
  current_time = datetime.now().strftime("%Y%m%d%H%M")
  tag_name = latest_release.get("tag_name", current_time)
  release_dir = artifacts_dir / tag_name
  latest_txt = artifacts_dir / "latest.txt"

  # Check if we have latest.txt and if the tag matches
  cached_tag = None
  if latest_txt.exists():
    with open(latest_txt, "r") as f:
      cached_tag = f.read().strip()

  # If tags match and release directory exists with content, use cache
  if cached_tag == tag_name and release_dir.exists() and any(release_dir.iterdir()):
    print(f"Using cached artifacts for release {tag_name} from {release_dir}")
  else:
    print(f"Downloading artifacts for release {tag_name}...")
    # Remove existing release directory if it exists (incomplete download)
    if release_dir.exists():
      import shutil

      shutil.rmtree(release_dir)

    release_dir.mkdir(exist_ok=True)

    # Save the release JSON data
    release_json_path = release_dir / "release.json"
    with open(release_json_path, "w") as f:
      json.dump(latest_release, f, indent=2)
      print(f"Saved release metadata to {release_json_path}")

    # Download all assets from the release
    for asset in latest_release.get("assets", []):
      asset_name = asset["name"]
      download_url = asset["browser_download_url"]
      asset_path = release_dir / asset_name

      print(f"Downloading {asset_name}...")
      response = requests.get(download_url, stream=True)
      response.raise_for_status()

      with open(asset_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
          f.write(chunk)

      # On Unix-like systems (macOS/Linux), make binary files executable
      if os.name == "posix" and not asset_name.endswith((".json", ".txt", ".md")):
        os.chmod(asset_path, 0o755)  # rwxr-xr-x
        print(f"Made {asset_name} executable")

    # Update latest.txt with the new tag
    with open(latest_txt, "w") as f:
      f.write(tag_name)
    print(f"Updated latest.txt with tag {tag_name}")

  return release_dir


if __name__ == "__main__":
  download_release_artifacts()

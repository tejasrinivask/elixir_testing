"""
Util functions
"""

import base64
import os

import requests


def github_read_file(org, repo, file_path, tag_name, github_token=None):
    """
    returns file contents from github
    """
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    url = (
        f"https://api.github.com/repos/{org}/{repo}/contents/{file_path}?ref={tag_name}"
    )
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    file_content = data["content"]
    file_content_encoding = data.get("encoding")
    if file_content_encoding == "base64":
        file_content = base64.b64decode(file_content).decode()

    return file_content


def main():
    """
    main function
    """
    github_token = os.environ["GITHUB_TOKEN"]
    org = "amagimedia"
    repo = "blip"
    file_path = "releases.yaml"
    tag_name = "v8.6.12"
    file_content = github_read_file(
        org, repo, file_path, tag_name, github_token=github_token
    )
    print(file_content)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import json
import os
import sys

import requests
from github import Github
from ruamel.yaml import YAML


def get_release_url(repo_full_name, tag_name, access_token):
    url = f"https://api.github.com/repos/{repo_full_name}/releases/tags/{tag_name}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    res_url = ""
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            res_url = response.json()["url"]
        else:
            print(f"Failed to update release: {response.status_code} - {response.text}")
    except Exception as err:
        print(f"Failed getting tag details with error: {err}")
    return res_url


def update_release(repo_full_name, release_id, new_body, access_token):
    url = f"https://api.github.com/repos/{repo_full_name}/releases/{release_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = {"body": new_body}
    response = requests.patch(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        print("Release updated successfully!")
    else:
        print(f"Failed to update release: {response.status_code} - {response.text}")


def get_release_body_from_build_notes():
    org = "tejasrinivask"
    yaml = YAML()
    body = "### Jira Changes\n"
    body += "| Jira ID | PR | Type | Description |\n"
    body += "| --- | --- | --- | --- |\n"
    try:
        with open("build_notes.yaml", mode="r", encoding="utf-8") as fh:
            data = yaml.load(fh)
        for each_entry in data["BuildNotes"]["Changes"]:
            pr_list = []
            for x in each_entry("pr", "").split(","):
                if x:
                    pr_list.append(f"#{x.strip()}")
            final_pr_str = ", ".join(pr_list)
            body += f"| https://amagiengg.atlassian.net/browse/{each_entry['JiraID']} | {final_pr_str} | {each_entry['type']} | {each_entry['description']} |\n"
    except Exception as e:
        print(f"Error loading build_notes, err: {e}")
        return ""
    return body


def upload_asset(release, file_name, label):
    try:
        asset = release.upload_asset(file_name, label=label)
        print(f"Asset uploaded: {asset.name} ({asset.browser_download_url})")
    except Exception as err:
        print(f"Failed uploading {file_name} as release asset with error: {err}")


def create_tag(tag_name, repo_full_name, token, sha):
    g = Github(token)
    repo_owner, repo_name = repo_full_name.split("/")
    repo = g.get_repo(f"{repo_owner}/{repo_name}")
    # create tag and release from pr
    release_tag = repo.create_git_tag_and_release(
        tag_name, tag_name, tag_name, tag_name, sha, "commit", draft=False
    )
    print(f"The link to the created release: {release_tag.html_url}")
    release = repo.get_release(tag_name)
    if release:
        upload_asset(release, "build_notes.yaml", "Release Notes")
    else:
        print(f"No release found for tag: {tag_name}")


def main():
    tag_name = sys.argv[1]
    repo_full_name = sys.argv[2]
    sha = sys.argv[3]
    token = os.environ.get("GH_TOKEN", None)
    try:
        create_tag(tag_name, repo_full_name, token, sha)
        url = get_release_url(repo_full_name, tag_name, token)
        if not url:
            print("Getting url failed, not updating release details")
            sys.exit(0)
        release_id = url.split("/")[-1]
        new_body = get_release_body_from_build_notes()
        update_release(repo_full_name, release_id, new_body, token)
    except Exception as err:
        print(f"Failed to create tag with error: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

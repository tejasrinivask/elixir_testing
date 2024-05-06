#!/usr/bin/env python3

from github import Github
import os
import sys
import requests
from requests.auth import HTTPBasicAuth
import time

def upload_asset (release, file_name, label):
    with open(file_name, 'r') as file:
        print (f"{file_name} yaml file loaded")
    asset = release.upload_asset(file_name, label=label)
    print (f"Asset uploaded: {asset.name} ({asset.browser_download_url})")

def create_tag(tag_name, branch, repo_full_name, token, sha):
    g = Github(token)
    repo_owner, repo_name = repo_full_name.split('/')
    repo = g.get_repo(f"{repo_owner}/{repo_name}")
    # create tag and release from pr
    release_tag = repo.create_git_tag_and_release(tag_name, tag_name, tag_name, tag_name, sha, 'commit', draft=False)
    print(f'The link to the created release: {release_tag.html_url}')
    release = repo.get_release(tag_name)
    if release:
            upload_asset (release, 'build_notes.yaml', "Release Notes")
    else:
        print(f"No release found for tag: {tag_name}")


if __name__ == "__main__":
    tag_name = sys.argv[1]
    branch = sys.argv[2]
    repo_full_name = sys.argv[3]
    sha = sys.argv[4]
    token = os.environ.get("GH_TOKEN", None)
    try:
        create_tag(tag_name, branch, repo_full_name, token, sha)
    except Exception as err:
        print (f"Failed to create tag with error: {err}")

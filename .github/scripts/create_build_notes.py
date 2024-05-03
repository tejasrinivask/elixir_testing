#!/usr/bin/env python3

import json
import os
import requests
import sys

def main():
    GIT_REPO = sys.argv[1]
    BASE_BRANCH = sys.argv[2]
    LAST_TAG = sys.argv[3]
    CURRENT_TAG = sys.argv[4]
    GIT_TOKEN = os.environ.get('GIT_TOKEN', None)
    if not GIT_TOKEN:
        print("Not able to get GIT_TOKEN")
        exit(1)
    # in body "target_commitish" is optional if the "tag_name" already exists
    # if "tag_name" doesn't exist then "target_commitish" is used
    pr_list_res = requests.post(
        f"https://api.github.com/repos/{GIT_REPO}/releases/generate-notes",
        headers={
            "Authorization": f"Bearer {GIT_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "tag_name": CURRENT_TAG,
            "target_commitish": BASE_BRANCH,
            "previous_tag_name": LAST_TAG,
        },
    ).json()
    lines = pr_list_res["body"].splitlines()
    pr_list = []
    pr_info_list = []
    for line in lines:
        if line.startswith('* '):
            res = line.rsplit('/',1)
            pr_list.append(res[1])
            pr_info = requests.get(
            f"https://api.github.com/repos/{GIT_REPO}/pulls/{res[1]}",
            headers={
                "Authorization": f"Bearer {GIT_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            },
            ).json()
            pr_info_list.append(pr_info)
    print("\n".join(pr_list))


if __name__ == '__main__':
    main()

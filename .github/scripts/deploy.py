#!/usr/bin/env python3
"""
Update branch pattern for pull request validator workflow
"""
import sys
import json
import os

from ruamel.yaml import YAML


def main():
    """
    update branch pattern for pr_body_validator workflow file
    """
    branch_pattern = sys.argv[1]
    curr_path = os.path.abspath(__file__)
    dir_path = os.path.dirname(curr_path)
    root_path = os.path.dirname(os.path.dirname(dir_path))
    tgt_path = os.path.join(
        root_path, "target_repo", ".github", "scripts", "build_notes_configs.json"
    )
    with open(
        tgt_path,
        mode="r",
        encoding="utf-8",
    ) as fh:
        data = json.load(fh)
    data["branch_pattern"] = branch_pattern
    with open(tgt_path, mode="w", encoding="utf-8") as fh:
        json.dump(data, fh)


if __name__ == "__main__":
    main()

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
    print(curr_path)
    print(dir_path)
    tgt_path = os.path.join(
        root_path, "target_repo", ".github", "scripts", "build_notes_configs.json"
    )
    print(tgt_path)
    with open(
        tgt_path,
        mode="r",
        encoding="utf-8",
    ) as fh:
        data = json.load(fh)
    data["branch_pattern"] = branch_pattern
    # yaml = YAML()
    # with open(
    #     "target_repo/.github/workflows/pr_body_validator.yaml",
    #     mode="r",
    #     encoding="utf-8",
    # ) as fh:
    #     data = yaml.load(fh)
    # cmd = [i.strip() for i in data["jobs"]["BlockPR"]["steps"][1]["run"].split()[:3]]
    # for pat in branch_pattern.split():
    #     cmd.append(f"{pat}")
    # data["jobs"]["BlockPR"]["steps"][1]["run"] = " ".join(cmd)
    # with open(
    #     "target_repo/.github/workflows/pr_body_validator.yaml",
    #     mode="w",
    #     encoding="utf-8",
    # ) as fh:
    #     yaml.dump(data, fh)


if __name__ == "__main__":
    main()

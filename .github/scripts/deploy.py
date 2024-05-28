#!/usr/bin/env python3
"""
Update branch pattern for pull request validator workflow
"""
import sys

from ruamel.yaml import YAML


def main():
    """
    update branch pattern for pr_body_validator workflow file
    """
    branch_pattern = sys.argv[1]
    yaml = YAML()
    with open(
        "target_repo/.github/workflows/pr_body_validator.yaml",
        mode="r",
        encoding="utf-8",
    ) as fh:
        data = yaml.load(fh)
    cmd = [i.strip() for i in data["jobs"]["BlockPR"]["steps"][1]["run"].split()[:-1]]
    for pat in branch_pattern.split():
        cmd.append(f"'{pat}'")
    data["jobs"]["BlockPR"]["steps"][1]["run"] = " ".join(cmd)
    with open(
        "target_repo/.github/workflows/pr_body_validator.yaml",
        mode="w",
        encoding="utf-8",
    ) as fh:
        yaml.dump(data, fh)


if __name__ == "__main__":
    main()

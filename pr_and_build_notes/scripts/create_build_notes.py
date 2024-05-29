#!/usr/bin/env python3

import json
import os
import re
import sys
from collections import defaultdict

import requests
from jira import Jira
from pr_body_validatior import execute_action_based_on_branch, validate_branches
from ruamel.yaml import YAML

GH_TOKEN = os.environ.get("GH_TOKEN", None)
BUILD_NOTES = "BuildNotes"
BUILD_DATE = "Date"
CONFIG_CHANGES = "Config Changes"
CONFIG_CHANGES_NEW = "New"
CONFIG_CHANGES_MOD = "Changed"
CONFIG_CHANGES_DEPR = "Deprecated"
CONFIG_CHANGES_REM = "Removed"
DEPRECATED_FEATURES = "Deprecated Features"
LIMITATIONS = "Limitations"
DEPENDENCIES = "Dependencies"
COMPONENT_RELEASES = "Component Releases"
JIRA_CHANGES = "Changes"
MAIN_JIRA_LIST = ["CRP", "CPRE", "CLI", "NPIE", "PIE"]


def execute_action_based_on_tag(prefix_tags, suffix_tags, contain_tags, tag):
    """
    Skips the github action in the following scenarios:
    - if the base branch is of type provided in any of the lists

    Params:
    prefix_tags: list
    suffix_tags: list
    contain_tags: list
    base_branch: str

    Returns:
    bool, bool
    first return type gives the result if the action should be skipped or not if the prefix is '+'. If the prefix is '-' caller should reverse it and use
    second return param indicates if the skip is because of head ref. It will be true only if the pr is revert pr or build notes gen pr
    """
    for pre in prefix_tags:
        if tag.startswith(pre):
            print(f"Matches with prefix -> {pre}")
            return True
    for suf in suffix_tags:
        if tag.endswith(suf):
            print(f"Matches with suffix -> {suf}")
            return True
    for pattern in contain_tags:
        if pattern in tag:
            print(f"Matches with pattern -> {pattern}")
            return True
    return False


def validate_tag(tag_name):
    """
    Parse tags provided in the arguments and returns 3 lists of tags
    prefix_tags -> format +*(tag_prefix)
    suffix_tags -> format +(tag_suffix)*
    contain_tags -> format +*(tag_contains_string)*

    Exits if tag format doesn't start with "+" or unknown format.

    Params:
    None

    Returns:
    3 lists of tags with the provided arguments, namely:
    prefix_tags -> list
    suffix_tags -> list
    contain_tags -> list
    is_it_plus -> bool, will be True if the prefix '+', else False for '-'
    """
    prefix_tags, suffix_tags, contain_tags = [], [], []
    is_it_plus = False
    with open(
        ".github/scripts/build_notes_configs.json", mode="r", encoding="utf-8"
    ) as fh:
        data = json.load(fh)
    tags = [x.strip() for x in data["tag_pattern"].split()]
    if not tags:
        print("No tags provided, updating taglist")
        return True
    symbol = ""
    if tags[0].startswith("+"):
        symbol = "+"
        is_it_plus = True
    elif tags[0].startswith("-"):
        symbol = "-"
        is_it_plus = False
    else:
        print(f"Unknown tag format -> {tags[0]}")
        sys.exit(1)
    for tag in tags:
        if not tag.startswith(symbol):
            print(
                f"All the tags should be starting with the same prefix: {symbol}, error -> {tag}"
            )
            sys.exit(1)
        each_tag = tag[1:]  # ignore + in the beginning
        if each_tag[0] == "*" and each_tag[-1] == "*":  # format -> +*(tag)*
            contain_tags.append(each_tag[each_tag.find("(") + 1 : each_tag.find(")")])
        elif each_tag[0] == "*":  # format -> +*(tag)
            suffix_tags.append(each_tag[each_tag.find("(") + 1 : each_tag.find(")")])
        elif each_tag[-1] == "*":  # format -> +(tag)*
            prefix_tags.append(each_tag[each_tag.find("(") + 1 : each_tag.find(")")])
        else:
            print(f"Unknown tag format -> {tag}")
            sys.exit(1)
    # return prefix_tags, suffix_tags, contain_tags, is_it_plus
    result = execute_action_based_on_tag(
        prefix_tags, suffix_tags, contain_tags, tag_name
    )
    if not result:
        if is_it_plus:
            print(
                f"{tag_name} did not match with any patterns and the prefix is '+'. Not updating taglislt."
            )
            return False
    if result and not is_it_plus:
        print(
            f"{tag_name} matches with a pattern and the prefix is '-'. Not updating taglislt."
        )
        return False
    return True


def update_taglist(tag_name: str, base_branch: str, head_branch: str) -> bool:
    """
    returns if taglist should be updated based on tag name, base branch, head_branch
    """
    prefix_branches, suffix_branches, contain_branches, is_it_plus = validate_branches()
    result, is_it_because_of_head_ref = execute_action_based_on_branch(
        prefix_branches, suffix_branches, contain_branches, base_branch, head_branch
    )

    if not result:
        if is_it_because_of_head_ref:
            return False
        if is_it_plus:
            return False
    if result and not is_it_plus:
        return False
    return validate_tag(tag_name)


def cleanup_generated_yaml_data(yaml_data, date, tag, author):
    final_yaml_data = {
        BUILD_NOTES: {
            BUILD_DATE: date,
            "Tag": tag,
            "Author": author,
            JIRA_CHANGES: [],
            CONFIG_CHANGES: {},
        }
    }
    if "jira" in yaml_data:
        for k, v in yaml_data["jira"].items():
            final_yaml_data[BUILD_NOTES][JIRA_CHANGES].append(
                {
                    "JiraID": k,
                    "pr": ", ".join(v["PR"]),
                    "type": v["Type"],
                    "component": ", ".join(v["Component"]),
                    "description": ", ".join(v["Description"]),
                    "stepstoreproduce": ", ".join(v["StepsToReproduce"]),
                    "impacts": ", ".join(v["Impact"]),
                }
            )
    if "new" in yaml_data:
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_NEW] = []
        files_list = []
        for k, v in yaml_data["new"].items():
            files_list.append(
                {
                    "file": k,
                    "changes": v,
                }
            )
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_NEW].append(
            {"component": author, "files": files_list}
        )
    if "changed" in yaml_data:
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_MOD] = []
        files_list = []
        for k, v in yaml_data["changed"].items():
            files_list.append(
                {
                    "file": k,
                    "changes": v,
                }
            )
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_MOD].append(
            {"component": author, "files": files_list}
        )
    if "removed" in yaml_data:
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_REM] = []
        files_list = []
        for k, v in yaml_data["removed"].items():
            files_list.append(
                {
                    "file": k,
                    "changes": v,
                }
            )
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_REM].append(
            {"component": author, "files": files_list}
        )
    if "deprecated" in yaml_data:
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_DEPR] = []
        files_list = []
        for k, v in yaml_data["deprecated"].items():
            files_list.append(
                {
                    "file": k,
                    "changes": v,
                }
            )
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_DEPR].append(
            {"component": author, "files": files_list}
        )
    if "limitations" in yaml_data:
        final_yaml_data[BUILD_NOTES][LIMITATIONS] = yaml_data["limitations"]
    if "dependencies" in yaml_data:
        final_yaml_data[BUILD_NOTES][DEPENDENCIES] = yaml_data["dependencies"]
    if "Deprecated Features" in yaml_data:
        final_yaml_data[BUILD_NOTES][DEPRECATED_FEATURES] = yaml_data[
            "Deprecated Features"
        ]
    return final_yaml_data


def get_jira_ids_for_multiple_entries(data):
    """
    CRP, GAMMA -> Only CRP
    CRP, CPRE, GAMMA -> CRP & CPRE in 2 rows (ignore GAMMA)
    GAMMA -> Picked as entry
    CRP, CPRE, NPIE -> Split into 3 rows
    GAMMA, GAMMA -> Split into 2 rows and fill description from Jira
    """
    api_token = os.environ.get("JIRA_PASSWORD", "")
    jira = Jira(api_token)
    return_dict = {}
    jira_ids_list = [x.strip() for x in data.split(",")]
    d = defaultdict(list)
    """
    sampel value for 'd'
    {
        "CRP": ["CRP-1", "CRP-2"],
        "GAMMA": ["GAMMA-1"],
        "NPIE": ["NPIE-1"],
    }
    """
    comp_ticket_count = 0
    for k, v in [(i.split("-")[0], i) for i in jira_ids_list]:
        d[k].append(v)
        if k not in MAIN_JIRA_LIST:
            comp_ticket_count += 1
    ignore_comp_tickets = False
    if comp_ticket_count != len(jira_ids_list):
        ignore_comp_tickets = True
    for k, v in d.items():
        if k not in MAIN_JIRA_LIST and ignore_comp_tickets:
            continue
        for each_id in v:
            try:
                data = jira.get(
                    each_id
                )  # data should always exist as pr is validated & merged
                return_dict[each_id] = data["fields"]["summary"]
            except Exception as err:
                print(f"Failed getting data for issue -> {each_id} with error {err}")
                continue
    return return_dict


def generate_build_notes(final_dict):
    yaml_data = {}
    for pr_number, pr_data in final_dict.items():
        if JIRA_CHANGES in pr_data:
            if "jira" not in yaml_data:
                yaml_data["jira"] = {}
            for e in pr_data[JIRA_CHANGES]["data"]:
                if "," in e["Jira ID"]:  # handle comma separated jira ids
                    d = get_jira_ids_for_multiple_entries(e["Jira ID"])
                    for issue, desc in d.items():
                        if issue not in yaml_data["jira"]:
                            yaml_data["jira"][issue] = {
                                "PR": [str(pr_number)],
                                "Type": e["Type"],
                                "Component": [e["Component name"]],
                                "Description": [desc],
                                "StepsToReproduce": [
                                    e["Steps to reproduce & validate"]
                                ],
                                "Impact": [e["Impact on other features/components"]],
                            }
                        else:
                            yaml_data["jira"][issue]["PR"].append(str(pr_number))
                            yaml_data["jira"][issue]["Component"].append(
                                e["Component name"]
                            )
                            yaml_data["jira"][issue]["Description"].append(desc)
                            yaml_data["jira"][issue]["StepsToReproduce"].append(
                                e["Steps to reproduce & validate"]
                            )
                            yaml_data["jira"][issue]["Impact"].append(
                                e["Impact on other features/components"]
                            )
                else:
                    if e["Jira ID"] not in yaml_data["jira"]:
                        yaml_data["jira"][e["Jira ID"]] = {
                            "PR": [str(pr_number)],
                            "Type": e["Type"],
                            "Component": [e["Component name"]],
                            "Description": [e["Change Description"]],
                            "StepsToReproduce": [e["Steps to reproduce & validate"]],
                            "Impact": [e["Impact on other features/components"]],
                        }
                    else:
                        yaml_data["jira"][e["Jira ID"]]["PR"].append(str(pr_number))
                        yaml_data["jira"][e["Jira ID"]]["Component"].append(
                            e["Component name"]
                        )
                        yaml_data["jira"][e["Jira ID"]]["Description"].append(
                            e["Change Description"]
                        )
                        yaml_data["jira"][e["Jira ID"]]["StepsToReproduce"].append(
                            e["Steps to reproduce & validate"]
                        )
                        yaml_data["jira"][e["Jira ID"]]["Impact"].append(
                            e["Impact on other features/components"]
                        )
        if "New Configs" in pr_data and pr_data["New Configs"]["data"]:
            if "new" not in yaml_data:
                yaml_data["new"] = {}
            for e in pr_data["New Configs"]["data"]:
                if e["file"] not in yaml_data["new"]:
                    yaml_data["new"][e["file"]] = [
                        {
                            "keyPath": e["keyPath"],
                            "description": e["description"],
                            "mandatory": e["mandatory"],
                            "type": e["type"],
                            "allowed-value": e["allowed-value"],
                            "default-value": e["default-value"],
                            "sample-value": e["sample-value"],
                        }
                    ]
                else:
                    yaml_data["new"][e["file"]].append(
                        {
                            "keyPath": e["keyPath"],
                            "description": e["description"],
                            "mandatory": e["mandatory"],
                            "type": e["type"],
                            "allowed-value": e["allowed-value"],
                            "default-value": e["default-value"],
                            "sample-value": e["sample-value"],
                        }
                    )
        if "Changed Configs" in pr_data and pr_data["Changed Configs"]["data"]:
            if "changed" not in yaml_data:
                yaml_data["changed"] = {}
            for e in pr_data["Changed Configs"]["data"]:
                if e["file"] not in yaml_data["changed"]:
                    yaml_data["changed"][e["file"]] = [
                        {
                            "keyPath": e["keyPath"],
                            "description": e["description"],
                            "mandatory": e["mandatory"],
                            "type": e["type"],
                            "allowed-value": e["allowed-value"],
                            "default-value": e["default-value"],
                            "sample-value": e["sample-value"],
                        }
                    ]
                else:
                    yaml_data["changed"][e["file"]].append(
                        {
                            "keyPath": e["keyPath"],
                            "description": e["description"],
                            "mandatory": e["mandatory"],
                            "type": e["type"],
                            "allowed-value": e["allowed-value"],
                            "default-value": e["default-value"],
                            "sample-value": e["sample-value"],
                        }
                    )
        if "Removed Configs" in pr_data and pr_data["Removed Configs"]["data"]:
            if "removed" not in yaml_data:
                yaml_data["removed"] = {}
            for e in pr_data["Removed Configs"]["data"]:
                if e["file"] not in yaml_data["changed"]:
                    yaml_data["removed"][e["file"]] = [
                        {
                            "keyPath": e["keyPath"],
                            "description": e["description"],
                        }
                    ]
                else:
                    yaml_data["removed"][e["file"]].append(
                        {
                            "keyPath": e["keyPath"],
                            "description": e["description"],
                        }
                    )
        if "Deprecated Configs" in pr_data and pr_data["Deprecated Configs"]["data"]:
            if "deprecated" not in yaml_data:
                yaml_data["deprecated"] = {}
            for e in pr_data["Deprecated Configs"]["data"]:
                if e["file"] not in yaml_data["changed"]:
                    yaml_data["deprecated"][e["file"]] = [
                        {
                            "keyPath": e["keyPath"],
                            "description": e["description"],
                        }
                    ]
                else:
                    yaml_data["deprecated"][e["file"]].append(
                        {
                            "keyPath": e["keyPath"],
                            "description": e["description"],
                        }
                    )
        if LIMITATIONS in pr_data:
            if "limitations" not in yaml_data:
                yaml_data["limitations"] = []
            for e in pr_data[LIMITATIONS]["data"]:
                yaml_data["limitations"].append(e["Limitations"])
        if DEPENDENCIES in pr_data:
            if "dependencies" not in yaml_data:
                yaml_data["dependencies"] = []
            for e in pr_data[DEPENDENCIES]["data"]:
                yaml_data["dependencies"].append(e["Dependencies"])
        if DEPRECATED_FEATURES in pr_data:
            if "Deprecated Features" not in yaml_data:
                yaml_data["Deprecated Features"] = []
            for e in pr_data[DEPRECATED_FEATURES]["data"]:
                yaml_data["Deprecated Features"].append(e["Deprecated Features"])
    return yaml_data


def get_pr_body(pr_info_list):
    final_dict = {}
    for item in pr_info_list:
        number = item["number"]
        data = markdown_tables_to_dicts(item["body"])
        if not data:
            continue
        final_dict[number] = data
    return final_dict


def markdown_tables_to_dicts(markdown_text):
    tables = {}
    current_table = None
    if not markdown_text or not markdown_text.startswith(
        "### Changes"
    ):  # Check if the pull request start with expected md format
        return tables
    lines = markdown_text.strip().split("\n")
    skip_section = False
    for line in lines:
        if re.match(r"^#+\s+\w+", line):  # Check for headings
            current_table = None
            table_name = line.strip("#").strip()
            if table_name == "PR changes":
                skip_section = True
                continue
            else:
                skip_section = False
            if table_name not in tables:
                tables[table_name] = {}
                # skip_rows_count variable shows the rows count that needs to be skipped.
                # creating new table needs setting up header row, hence the row (separator row) after that will be skipped.
                tables[table_name]["skip_rows_count"] = 1
            else:
                # if the table already exists, then header and separator rows needs to be skipped.
                tables[table_name]["skip_rows_count"] = 2
            current_table = tables[table_name]
        elif re.match(r"^\s*\|.*\|\s*$", line):  # Check for table rows
            if not skip_section:
                if current_table is not None:
                    if "headers" not in current_table:
                        current_table["headers"] = [
                            header.strip()
                            for header in line.strip("|").split("|")
                            if header.strip()
                        ]
                        current_table["data"] = []
                    else:
                        # skip_rows_count values as '0' indicates that the current row is data row
                        if current_table["skip_rows_count"] == 0:
                            row_data = [
                                data.strip() for data in line.strip("|").split("|")
                            ]
                            if current_table["data"] or any(
                                cell.strip() for cell in row_data
                            ):
                                current_table["data"].append(
                                    dict(zip(current_table["headers"], row_data))
                                )
                        else:
                            current_table["skip_rows_count"] -= 1
    return tables


def get_payload_for_generating_release_notes(tag, base):
    """
    1. returns payload for generate-notes api call
    2. creates taglist.yaml if it doesn't exist
    3. updates taglist.yaml if it exists
    """
    # open taglist.yaml
    yaml = YAML()
    default_data = {"Tag List": [tag]}
    payload_json = {
        "tag_name": tag,
        "target_commitish": base,
    }
    path = "taglist.yaml"
    taglist_update = validate_tag(tag)
    data = {}
    if not os.path.exists(path) or not os.path.isfile(path):
        if taglist_update:
            print(f"{path} doesn't exist, creating ...")
            with open(path, mode="w", encoding="utf-8") as fh:
                yaml.dump(default_data, fh)
        return payload_json, True
    with open(path, mode="r", encoding="utf-8") as fh:
        data = yaml.load(fh)
    with open(path, mode="w", encoding="utf-8") as fh:
        try:
            last_tag = data["Tag List"][-1]
            payload_json["previous_tag_name"] = last_tag
            if taglist_update:
                data["Tag List"].append(tag)
                yaml.dump(data, fh)
        except Exception as e:
            # continue with default payload even if there is exception
            print(f"falied getting last tag with error -> {e}")
    return payload_json, True


def create_release_files_with_pr_list(pr_list, DATE, CURRENT_TAG, GIT_REPO):
    pr_info_list = []
    for each_pr in pr_list:
        pr_info = requests.get(
            f"https://api.github.com/repos/{GIT_REPO}/pulls/{each_pr}",
            headers={
                "Authorization": f"Bearer {GH_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            },
        ).json()
        pr_info_list.append(pr_info)
    final_dict = get_pr_body(pr_info_list)
    yaml_data = generate_build_notes(final_dict)
    final_yaml_data = cleanup_generated_yaml_data(
        yaml_data, DATE, CURRENT_TAG, GIT_REPO.split("/")[-1]
    )
    yaml = YAML()
    with open("build_notes.yaml", mode="w", encoding="utf-8") as outfile:
        yaml.dump(final_yaml_data, outfile)


def main():
    GIT_REPO = sys.argv[1]
    BASE_BRANCH = sys.argv[2]
    # LAST_TAG = sys.argv[3]
    CURRENT_TAG = sys.argv[3]
    DATE = sys.argv[4]
    if not GH_TOKEN:
        print("Not able to get GH_TOKEN")
        exit(1)
    # in body "target_commitish" is optional if the "tag_name" already exists
    # if "tag_name" doesn't exist then "target_commitish" is used
    payload, status = get_payload_for_generating_release_notes(CURRENT_TAG, BASE_BRANCH)
    if not status:
        sys.exit(1)
    pr_list_res = requests.post(
        f"https://api.github.com/repos/{GIT_REPO}/releases/generate-notes",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=payload,
    ).json()
    lines = pr_list_res["body"].splitlines()
    pr_list = []
    for line in lines:
        if line.startswith("* "):
            res = line.rsplit("/", 1)
            pr_list.append(res[1])
    print(f"pr list -> {pr_list}")
    create_release_files_with_pr_list(pr_list, DATE, CURRENT_TAG, GIT_REPO)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import json
import os
import re
import requests
import sys
from ruamel.yaml import YAML


BUILD_NOTES             = "BuildNotes"
BUILD_DATE              = "Date"
CONFIG_CHANGES          = "Config Changes"
CONFIG_CHANGES_NEW      = "New"
CONFIG_CHANGES_MOD      = "Changed"
CONFIG_CHANGES_DEPR     = "Deprecated"
CONFIG_CHANGES_REM      = "Removed"
DEPRECATED_FEATURES     = "Deprecated Features"
LIMITATIONS             = "Limitations"
DEPENDENCIES            = "Dependencies"
COMPONENT_RELEASES      = "Component Releases"
JIRA_CHANGES            = "Changes"

def generate_build_notes(final_dict, date, tag, author):
    yaml_data = {
        BUILD_NOTES:{
            BUILD_DATE: date,
            "Tag": tag,
            "Author": author,
            JIRA_CHANGES: list(),
            CONFIG_CHANGES:{
                CONFIG_CHANGES_NEW:list(),
                CONFIG_CHANGES_MOD:list(),
                CONFIG_CHANGES_DEPR:list(),
                CONFIG_CHANGES_REM:list()
            },
            DEPRECATED_FEATURES:list(),
            LIMITATIONS:list(),
            DEPENDENCIES:list()
        }
    }
    for pr_number, pr_data in final_dict.items():
        if JIRA_CHANGES in pr_data:
            for entry in pr_data[JIRA_CHANGES]["data"]:
                yaml_data[BUILD_NOTES][JIRA_CHANGES].append(entry)
        if "New Configs" in pr_data and pr_data["New Configs"]["data"]:
            component = pr_data["New Configs"]["data"][0]["component"]
            files = []
            for entry in pr_data["New Configs"]["data"]:
                files.append(
                    {
                        "file": entry["file"],
                        "changes": [
                            {
                                "keyPath": entry["keyPath"],
                                "description": entry["description"],
                                "mandatory": entry["mandatory"],
                                "type": entry["type"],
                                "allowed-value": entry["allowed-value"],
                                "default-value": entry["default-value"],
                                "sample-value": entry["sample-value"],
                            }
                        ]
                    }
                )
            yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_NEW].append(
                {
                    "component": component,
                    "files": files,
                }
            )
        if "Changed Configs" in pr_data and pr_data["Changed Configs"]["data"]:
            component = pr_data["Changed Configs"]["data"][0]["component"]
            files = []
            for entry in pr_data["Changed Configs"]["data"]:
                files.append(
                    {
                        "file": entry["file"],
                        "changes": [
                            {
                                "keyPath": entry["keyPath"],
                                "description": entry["description"],
                                "mandatory": entry["mandatory"],
                                "type": entry["type"],
                                "allowed-value": entry["allowed-value"],
                                "default-value": entry["default-value"],
                                "sample-value": entry["sample-value"],
                            }
                        ]
                    }
                )
            yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_MOD].append(
                {
                    "component": component,
                    "files": files,
                }
            )
        if "Removed Configs" in pr_data and pr_data["Removed Configs"]["data"]:
            component = pr_data["Removed Configs"]["data"][0]["component"]
            files = []
            for entry in pr_data["Removed Configs"]["data"]:
                files.append(
                    {
                        "file": entry["file"],
                        "changes": [
                            {
                                "keyPath": entry["keyPath"],
                                "description": entry["description"],
                            }
                        ]
                    }
                )
            yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_REM].append(
                {
                    "component": component,
                    "files": files,
                }
            )
        if "Deprecated Configs" in pr_data and pr_data["Deprecated Configs"]["data"]:
            component = pr_data["Deprecated Configs"]["data"][0]["component"]
            files = []
            for entry in pr_data["Deprecated Configs"]["data"]:
                files.append(
                    {
                        "file": entry["file"],
                        "changes": [
                            {
                                "keyPath": entry["keyPath"],
                                "description": entry["description"],
                            }
                        ]
                    }
                )
            yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_REM].append(
                {
                    "component": component,
                    "files": files,
                }
            )
        if LIMITATIONS in pr_data:
            for entry in pr_data[LIMITATIONS]["data"]:
                yaml_data[BUILD_NOTES][LIMITATIONS].append(entry)
        if DEPENDENCIES in pr_data:
            for entry in pr_data[DEPENDENCIES]["data"]:
                yaml_data[BUILD_NOTES][DEPENDENCIES].append(entry)
        if DEPRECATED_FEATURES in pr_data:
            for entry in pr_data[DEPRECATED_FEATURES]["data"]:
                yaml_data[BUILD_NOTES][DEPRECATED_FEATURES].append(entry)
    return yaml_data

def get_pr_body(pr_info_list):
    final_dict = {}
    for item in pr_info_list:
        number = item['number']
        data = markdown_tables_to_dicts(item['body'])
        final_dict[number] = data
    return final_dict

def markdown_tables_to_dicts(markdown_text):
    tables = {}
    current_table = None
    lines = markdown_text.strip().split('\n')
    skip_section = False
    for line in lines:
        if re.match(r'^#+\s+\w+', line):  # Check for headings
            current_table = None
            table_name = line.strip('#').strip()
            if table_name == "PR changes":
                skip_section = True
                continue
            else:
                skip_section = False
            if table_name not in tables:
                tables[table_name] = {}
                # skip_rows_count variable shows the rows count that needs to be skipped.
                # creating new table needs setting up header row, hence the row (separator row) after that will be skipped.
                tables[table_name]['skip_rows_count'] = 1
            else:
                # if the table already exists, then header and separator rows needs to be skipped.
                tables[table_name]['skip_rows_count'] = 2
            current_table = tables[table_name]
        elif re.match(r'^\s*\|.*\|\s*$', line):  # Check for table rows
            if not skip_section:
                if current_table is not None:
                    if 'headers' not in current_table:
                        current_table['headers'] = [header.strip() for header in line.strip('|').split('|') if header.strip()]
                        current_table['data'] = []
                    else:
                        # skip_rows_count values as '0' indicates that the current row is data row
                        if current_table['skip_rows_count'] == 0:
                            row_data = [data.strip() for data in line.strip('|').split('|')]
                            if current_table['data'] or any(cell.strip() for cell in row_data):
                                current_table['data'].append(dict(zip(current_table['headers'], row_data)))
                        else:
                            current_table['skip_rows_count'] -= 1
    return tables

def main():
    GIT_REPO = sys.argv[1]
    BASE_BRANCH = sys.argv[2]
    LAST_TAG = sys.argv[3]
    CURRENT_TAG = sys.argv[4]
    DATE = sys.argv[5]
    GH_TOKEN = os.environ.get('GH_TOKEN', None)
    if not GH_TOKEN:
        print("Not able to get GH_TOKEN")
        exit(1)
    # in body "target_commitish" is optional if the "tag_name" already exists
    # if "tag_name" doesn't exist then "target_commitish" is used
    pr_list_res = requests.post(
        f"https://api.github.com/repos/{GIT_REPO}/releases/generate-notes",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
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
                "Authorization": f"Bearer {GH_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            },
            ).json()
            pr_info_list.append(pr_info)
    final_dict = get_pr_body(pr_info_list)
    yaml_data = generate_build_notes(final_dict, DATE, CURRENT_TAG, GIT_REPO.split('/')[-1])
    # print(yaml_data)
    yaml = YAML()
    with open('build_notes.yaml', 'w') as outfile:
        yaml.dump(yaml_data, outfile)


if __name__ == '__main__':
    main()

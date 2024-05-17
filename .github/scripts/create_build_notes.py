#!/usr/bin/env python3

import json
import os
import re
import requests
import sys
from collections import defaultdict
from ruamel.yaml import YAML
from jira import Jira


GH_TOKEN                = os.environ.get('GH_TOKEN', None)
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
MAIN_JIRA_LIST          = ["CRP", "CPRE", "CLI", "NPIE", "PIE"]

def cleanup_generated_yaml_data(yaml_data, date, tag, author):
    final_yaml_data = {
        BUILD_NOTES:{
            BUILD_DATE: date,
            "Tag": tag,
            "Author": author,
            JIRA_CHANGES: list(),
            CONFIG_CHANGES:{},
        }
    }
    if "jira" in yaml_data:
        for k, v in yaml_data["jira"].items():
            final_yaml_data[BUILD_NOTES][JIRA_CHANGES].append(
                {
                    "Jira ID": k,
                    "Description": ", ".join(v)
                }
            )
    if "new" in yaml_data:
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_NEW] = list()
        files_list = list()
        for k, v in yaml_data["new"].items():
            files_list.append(
                {
                    "file": k,
                    "changes": v,
                }
            )
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_NEW].append(
            {
                "component": author,
                "files": files_list
            }
        )
    if "changed" in yaml_data:
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_MOD] = list()
        files_list = list()
        for k, v in yaml_data["changed"].items():
            files_list.append(
                {
                    "file": k,
                    "changes": v,
                }
            )
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_MOD].append(
            {
                "component": author,
                "files": files_list
            }
        )
    if "removed" in yaml_data:
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_REM] = list()
        files_list = list()
        for k, v in yaml_data["removed"].items():
            files_list.append(
                {
                    "file": k,
                    "changes": v,
                }
            )
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_REM].append(
            {
                "component": author,
                "files": files_list
            }
        )
    if "deprecated" in yaml_data:
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_DEPR] = list()
        files_list = list()
        for k, v in yaml_data["deprecated"].items():
            files_list.append(
                {
                    "file": k,
                    "changes": v,
                }
            )
        final_yaml_data[BUILD_NOTES][CONFIG_CHANGES][CONFIG_CHANGES_DEPR].append(
            {
                "component": author,
                "files": files_list
            }
        )
    if "limitations" in yaml_data:
        final_yaml_data[BUILD_NOTES][LIMITATIONS] = yaml_data["limitations"]
    if "dependencies" in yaml_data:
        final_yaml_data[BUILD_NOTES][DEPENDENCIES] = yaml_data["dependencies"]
    if "Deprecated Features" in yaml_data:
        final_yaml_data[BUILD_NOTES][DEPRECATED_FEATURES] = yaml_data["Deprecated Features"]
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
    flag = False
    jira_ids_list = [x.strip() for x in data.split(",")]
    d = defaultdict(list)
    """
    d = {
        "CRP": ["CRP-1", "CRP-2"],
        "GAMMA": ["GAMMA-1"],
        "NPIE": ["NPIE-1"],
    }
    """
    comp_ticket_count = 0
    for k, v in [(i.split('-')[0], i) for i in jira_ids_list]:
        d[k].append(v)
        if k not in MAIN_JIRA_LIST:
            comp_ticket_count += 1
    ignore_comp_tickets = False
    if comp_ticket_count != len(jira_ids_list):
        ignore_comp_tickets = True
    for k, v in d.items():
        if k not in MAIN_JIRA_LIST and ignore_comp_tickets:
            continue
        else:
            for each_id in v:
                try:
                    data = jira.get(each_id)    # data should always exist as pr is validated & merged
                    return_dict[each_id] = data['fields']['summary']
                except Exception as err:
                    print(f"Failed getting data for issue -> {each_id} with error {err}")
                    continue
    return return_dict

def generate_build_notes(final_dict):
    yaml_data = dict()
    for pr_number, pr_data in final_dict.items():
        if JIRA_CHANGES in pr_data:
            if "jira" not in yaml_data:
                yaml_data["jira"] = dict()
            for e in pr_data[JIRA_CHANGES]["data"]:
                if "," in e["Jira ID"]:    # handle comma separated jira ids
                    d = get_jira_ids_for_multiple_entries(e["Jira ID"])
                    for issue, desc in d.items():
                        if issue not in yaml_data["jira"]:
                            yaml_data['jira'][issue] = [desc]
                        else:
                            yaml_data['jira'][issue].append(desc)
                else:
                    if e["Jira ID"] not in yaml_data["jira"]:
                        yaml_data["jira"][e["Jira ID"]] = [e["Change Description"]]
                    else:
                        yaml_data["jira"][e["Jira ID"]].append(e["Change Description"])
        if "New Configs" in pr_data and pr_data["New Configs"]["data"]:
            if "new" not in yaml_data:
                yaml_data["new"] = dict()
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
                yaml_data["changed"] = dict()
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
                yaml_data["removed"] = dict()
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
                yaml_data["deprecated"] = dict()
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
                yaml_data["limitations"] = list()
            for e in pr_data[LIMITATIONS]["data"]:
                yaml_data["limitations"].append(e["Limitations"])
        if DEPENDENCIES in pr_data:
            if "dependencies" not in yaml_data:
                yaml_data["dependencies"] = list()
            for e in pr_data[DEPENDENCIES]["data"]:
                yaml_data["dependencies"].append(e["Dependencies"])
        if DEPRECATED_FEATURES in pr_data:
            if "Deprecated Features" not in yaml_data:
                yaml_data["Deprecated Features"] = list()
            for e in pr_data[DEPRECATED_FEATURES]["data"]:
                yaml_data["Deprecated Features"].append(e["Deprecated Features"])
    return yaml_data

def get_pr_body(pr_info_list):
    final_dict = {}
    for item in pr_info_list:
        number = item['number']
        data = markdown_tables_to_dicts(item['body'])
        if not data:
            continue
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

def get_payload_for_generating_release_notes(tag, base):
    # open taglist.yaml
    yaml = YAML()
    default_data = {'Tag List': [tag]}
    payload_json={
        "tag_name": tag,
        "target_commitish": base,
    }
    path = 'taglist.yaml'
    data = {}
    if not os.path.exists(path) or not os.path.isfile(path):
        print(f"{path} doesn't exist, creating ...")
        with open(path, 'w') as fh:
            yaml.dump(default_data, fh)
        return payload_json, True
    with open(path, 'r') as fh:
        data = yaml.load(fh)
    with open(path, 'w') as fh:
        try:
            last_tag = data['Tag List'][-1]
            payload_json["previous_tag_name"] = last_tag
            data['Tag List'].append(tag)
            yaml.dump(data, fh)
        except Exception as e:
            print(f"falied getting last tag with error -> {e}")
            return {}, False
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
    final_yaml_data = cleanup_generated_yaml_data(yaml_data, DATE, CURRENT_TAG, GIT_REPO.split('/')[-1])
    yaml = YAML()
    with open('build_notes.yaml', 'w') as outfile:
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
        if line.startswith('* '):
            res = line.rsplit('/',1)
            pr_list.append(res[1])
    create_release_files_with_pr_list(pr_list, DATE, CURRENT_TAG, GIT_REPO)

if __name__ == '__main__':
    main()

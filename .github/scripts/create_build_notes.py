#!/usr/bin/env python3

import json
import os
import requests
import sys

def get_pr_body(pr_info_list):
    final_dict = {}
    for item in pr_info_list:
        number = item['number']
        body = item['body']
        data = markdown_tables_to_dicts(body)
        final_dict[number] = body
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
    # Not required, skip_rows_count will take care of removing separator row
    # Remove the first data entry (separator row) from each table
    # for table in tables.values():
    #     if table.get('data'):
    #         del table['data'][0]
    return tables

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
    final_dict = get_pr_body(pr_info_list)
    print(final_dict)


if __name__ == '__main__':
    main()

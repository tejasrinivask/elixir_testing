import concurrent.futures
import json
import os
import re
import sys

from jira import Jira

BUILD_NOTES_PR_BRANCH_FORMAT = "rc-build-notes-"
REVERT_PR_BRANCH_FORMAT = "revert-"


def check_if_jira_exists(password, issue_id):
    jira = Jira(password)
    response = jira.get(issue_id)
    if not response:
        return False
    return True


def thread_execution_for_jira(password, issue_list):
    return_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_item = {
            executor.submit(check_if_jira_exists, password, item): item
            for item in issue_list
        }
        for future in concurrent.futures.as_completed(future_to_item):
            item = future_to_item[future]
            try:
                data = future.result()
            except Exception as err:
                print(f"Failed getting data for {item} with error {err}")
            else:
                if data:
                    return_list.append(item)
                else:
                    print(f"No jira info for id {item}, exiting ...")
                    sys.exit(1)
    return return_list


def markdown_tables_to_dicts(markdown_text):
    tables = {}
    current_table = None
    lines = markdown_text.strip().split("\n")
    skip_section = False
    for line in lines:
        if re.match(r"^#+\s+\w+", line):  # Check for headings
            current_table = None
            table_name = line.strip("#").strip()
            if table_name == "Additional Info":
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
    # Not required, skip_rows_count will take care of removing separator row
    # Remove the first data entry (separator row) from each table
    # for table in tables.values():
    #     if table.get('data'):
    #         del table['data'][0]
    return tables


def execute_action_based_on_branch(
    prefix_branches, suffix_branches, contain_branches, base_branch, head_branch
):
    """
    Skips the github action in the following scenarios:
    - if the head_branch is from revert pr
    - if the head_branch is not of the build_notes branch format
    - if the base branch is of type provided in any of the lists

    Params:
    prefix_branches: list
    suffix_branches: list
    contain_branches: list
    base_branch: str
    head_branch: str

    Returns:
    bool, bool
    first return type gives the result if the action should be skipped or not if the prefix is '+'. If the prefix is '-' caller should reverse it and use
    second return param indicates if the skip is because of head ref. It will be true only if the pr is revert pr or build notes gen pr
    """
    if head_branch.startswith(REVERT_PR_BRANCH_FORMAT):  # skip check for build notes pr
        return False, True
    if head_branch.startswith(
        BUILD_NOTES_PR_BRANCH_FORMAT
    ):  # skip check for build notes pr
        return False, True
    for pre in prefix_branches:
        if base_branch.startswith(pre):
            print(f"Matches with prefix -> {pre}")
            return True, False
    for suf in suffix_branches:
        if base_branch.endswith(suf):
            print(f"Matches with suffix -> {suf}")
            return True, False
    for pattern in contain_branches:
        if base_branch.contains(pattern):
            print(f"Matches with pattern -> {pattern}")
            return True, False
    return False, False


def validate_branches():
    """
    Parse branches provided in the arguments and returns 3 lists of branches
    prefix_branches -> format +*(branch_prefix)
    suffix_branches -> format +(branch_suffix)*
    contain_branches -> format +*(branch_contains_string)*

    Exits if branch format doesn't start with "+" or unknown format.

    Params:
    None

    Returns:
    3 lists of branches with the provided arguments, namely:
    prefix_branches -> list
    suffix_branches -> list
    contain_branches -> list
    is_it_plus -> bool, will be True if the prefix '+', else False for '-'
    """
    prefix_branches, suffix_branches, contain_branches = [], [], []
    branches = sys.argv[1:]
    if not branches:
        print("No branches provided, skipping checks...")
        sys.exit(0)
    is_it_plus = False
    symbol = ""
    if branches[0].startswith("+"):
        symbol = "+"
        is_it_plus = True
    elif branches[0].startswith("-"):
        symbol = "-"
        is_it_plus = False
    else:
        print(f"Unknown branch format -> {branches[0]}")
        sys.exit(1)
    for branch in branches:
        if not branch.startswith(symbol):
            print(
                f"All the branches should be starting with the same prefix: {symbol}, error -> {branch}"
            )
            sys.exit(1)
        each_branch = branch[1:]  # ignore + in the beginning
        if each_branch[0] == "*" and each_branch[-1] == "*":  # format -> +*(branch)*
            contain_branches.append(
                each_branch[each_branch.find("(") + 1 : each_branch.find(")")]
            )
        elif each_branch[0] == "*":  # format -> +*(branch)
            suffix_branches.append(
                each_branch[each_branch.find("(") + 1 : each_branch.find(")")]
            )
        elif each_branch[-1] == "*":  # format -> +(branch)*
            prefix_branches.append(
                each_branch[each_branch.find("(") + 1 : each_branch.find(")")]
            )
        else:
            print(f"Unknown branch format -> {branch}")
            sys.exit(1)
    return prefix_branches, suffix_branches, contain_branches, is_it_plus


def skip_after_validating_description(body: str) -> bool:
    if "Skip PR validation" in body:
        return True
    return False


def main():
    # get the branches lists for validation
    prefix_branches, suffix_branches, contain_branches, is_it_plus = validate_branches()
    # load pull request event payload
    event_path = os.getenv("GITHUB_EVENT_PATH")
    # event_path validation
    if (
        not event_path
        or not os.path.exists(event_path)
        or not os.path.isfile(event_path)
    ):
        print(f"Failed getting event details from path: {event_path}")
        sys.exit(1)
    with open(event_path, mode="r", encoding="utf-8") as f:
        try:
            event_payload = json.load(f)
        except Exception as e:
            print("Error loading event payload, {e}")
            sys.exit(1)
    if (
        not event_payload
        or "pull_request" not in event_payload
        or not event_payload["pull_request"]
    ):
        print(f"Invalid event payload : {event_payload}")
        sys.exit(1)
    base_branch = event_payload["pull_request"]["base"]["ref"]
    head_branch = event_payload["pull_request"]["head"]["ref"]
    result, is_it_because_of_head_ref = execute_action_based_on_branch(
        prefix_branches, suffix_branches, contain_branches, base_branch, head_branch
    )
    if not result:
        if is_it_because_of_head_ref:
            print("Skipping check as it is either build notes pr or revert pr")
            sys.exit(0)
        if is_it_plus:
            print(
                f"{base_branch} did not match with any patterns and the prefix is '+'. Skipping check..."
            )
            sys.exit(0)
    if result and not is_it_plus:
        print(
            f"{base_branch} matches with a pattern and the prefix is '-'. Skipping check..."
        )
        sys.exit(0)
    markdown_text = event_payload["pull_request"]["body"]
    if skip_after_validating_description(markdown_text):
        print("Skipping PR validation")
        sys.exit(0)
    # Convert Markdown tables to dictionaries
    result = markdown_tables_to_dicts(markdown_text)
    # Store Jira id's in jira_list by parsing result
    jira_list = set()
    try:
        for each_entry in result["Changes"]["data"]:
            if each_entry["Jira ID"] != "":
                if "," in each_entry["Jira ID"]:
                    for item in each_entry["Jira ID"].split(","):
                        jira_list.add(item.strip())
                else:
                    jira_list.add(each_entry["Jira ID"])
    except Exception as err:
        print(f"Error while getting Jira ID's -> {err}")
    print(", ".join(jira_list))
    # Make Jira api call to validate if jira id actually exists
    jira_password = os.environ.get("JIRA_PASSWORD", "")
    if not jira_password:
        print("Skipping jira check as jira credentials are not")
        sys.exit(0)
    final_list = thread_execution_for_jira(jira_password, jira_list)
    if not final_list:
        print(f"No valid jira id's, exiting ...")
        sys.exit(1)
    print(f"Valid jira_list -> {final_list}")
    sys.exit(0)


if __name__ == "__main__":
    main()

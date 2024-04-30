import concurrent.futures
import json
import os
import re
import requests

PR_TITLE_PREFIX = "PR Merge"

def check_if_jira_exists(username, password, domain, issue_id):
    url = f"https://{domain}/rest/api/3/issue/{issue_id}"
    response = requests.get(url, auth=(username, password))
    if response.status_code == 404:
        return False
    return True

def thread_execution_for_jira(username, password, domain, issue_list):
    return_list = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_item = {executor.submit(check_if_jira_exists, username, password, domain, item): item for item in issue_list}
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
                    exit(1)
    return return_list

def markdown_tables_to_dicts(markdown_text):
    tables = {}
    current_table = None
    lines = markdown_text.strip().split('\n')

    skip_section = False
    for line in lines:
        print(line)
        if re.match(r'^#+\s+\w+', line):  # Check for headings
            print(f"current heading -> {line}")
            current_table = None
            table_name = line.strip('#').strip()
            if table_name == "PR changes":
                skip_section = True
                continue
            else:
                skip_section = False
            if table_name not in tables:
                tables[table_name] = {}
            current_table = tables[table_name]
        elif re.match(r'^\s*\|.*\|\s*$', line):  # Check for table rows
            print(f"table row -> {line}")
            if not skip_section:
                if current_table is not None:
                    if 'headers' not in current_table:
                        current_table['headers'] = [header.strip() for header in line.strip('|').split('|') if header.strip()]
                        current_table['data'] = []
                    else:
                        row_data = [data.strip() for data in line.strip('|').split('|')]
                        if current_table['data'] or any(cell.strip() for cell in row_data):
                            current_table['data'].append(dict(zip(current_table['headers'], row_data)))
        # else:
        #     print(f"Just a line -> {line}")

    # Remove the first data entry (separator row) from each table
    for table in tables.values():
        if table.get('data'):
            del table['data'][0]

    return tables

def main():
    # Load pull request event payload
    event_path = os.getenv('GITHUB_EVENT_PATH')
    with open(event_path, 'r') as f:
        try:
            event_payload = json.load(f)
        except Exception as e:
            print("Error loading event payload, {e}")
            exit(1)

    if not event_payload or 'pull_request' not in event_payload or not event_payload['pull_request']:
        print(f"Invalid event payload : {event_payload}")
        exit(1)

    print(event_payload)
    print(f"base branch -> {event_payload['pull_request']['base']}")
    markdown_text = event_payload['pull_request']['body']
    print("Printing markdown text")
    print(markdown_text)
    print("-----------end-----------")
    # Convert Markdown tables to dictionaries
    result = markdown_tables_to_dicts(markdown_text)
    print("Printing markdown to dict output")
    print(result)
    print("-----------end-----------")
    jira_list = []
    try:
        for each_entry in result["Changes"]["data"]:
            if each_entry["Jira ID"] != "":
                jira_list.append(each_entry["Jira ID"])
    except Exception as err:
        print(f"Error while getting Jira ID's -> {err}")
    print(", ".join(jira_list))
    # Format the dictionaries into YAML
    # yaml_output = yaml.dump(result, default_flow_style=False)
    # print(yaml_output)
    jira_uname = os.environ.get("JIRA_USERNAME", "")
    jira_password = os.environ.get("JIRA_PASSWORD", "")
    jira_domain = os.environ.get("JIRA_DOMAIN", "")
    if not jira_uname or not jira_password or not jira_domain:
        print("Skipping jira check as jira credentials are not")
        return
    final_list = thread_execution_for_jira(jira_uname, jira_password, jira_domain, jira_list)
    if not final_list:
        print(f"No valid jira id's, exiting ...")
        exit(1)
    print(f"valid jira_list -> {final_list}")
    exit(0)


if __name__ == '__main__':
    main()

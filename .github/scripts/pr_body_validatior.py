import json
import os
import re

PR_TITLE_PREFIX = "PR Merge"

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
    return return_list

def validate_pr_body(body):
    jira_list = []
    p = re.compile(r"^\s*\|\s*Jira ID\s*\|\s*")
    for each_line in body.splitlines():
        # print(each_line)
        m = p.match(each_line)
        if m:
            data = each_line[m.end():].rstrip(" |")
            if data:
                tmp_list = [x.strip() for x in data.split(",")]
                jira_list.extend(tmp_list)
    if not jira_list:
        print("No Jira ID's, exiting ...")
        exit(1)
    print(f"jira_list -> {jira_list}")
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
    return

def validate_pr_title(title):
    if PR_TITLE_PREFIX in title:
        print(f"Title has {PR_TITLE_PREFIX}")
    else:
        print(f"Title doesn't start with {PR_TITLE_PREFIX}")
        exit(1)

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

    # title = event_payload['pull_request']['title']
    # validate_pr_title(title)

    body = event_payload['pull_request']['body']
    validate_pr_body(body)


if __name__ == "__main__":
    main()

import json
import os
import re

PR_TITLE_PREFIX = "PR Merge"

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
        print("exiting")
        exit(1)
    print(jira_list)
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

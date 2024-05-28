"""
Updates jira id with the tag details
"""

import os
import sys

from jira import Jira
from ruamel.yaml import YAML

JIRA_PASSWORD = os.environ.get("JIRA_PASSWORD", None)
if not JIRA_PASSWORD:
    print(f"Jira password is empty, exiting...")
    sys.exit(1)


def main():
    yaml = YAML()
    data = {}
    jira = Jira(JIRA_PASSWORD)
    with open("build_notes.yaml", mode="r", encoding="utf-8") as fh:
        data = yaml.load(fh)
    for entry in data["BuildNotes"]["Changes"]:
        response_data = jira.get(entry["JiraID"])
        if not response_data:
            print(
                f"Jira issue: {entry['JiraID']} does not exist or user doesn't have permissions to access the issue"
            )
            sys.exit(1)
        try:
            current_payload = response_data["fields"]["customfield_12562"]
            # print(f"current_payload -> {current_payload}")
        except Exception as err:  # doesn't have the required custom field
            current_payload = ""
        payload_dict = jira.payload_str_to_dict(current_payload, entry)
        payload_as_str = jira.reconstruct_jira_payload_from_dict_to_str(payload_dict)
        jira.put(entry["JiraID"], payload=payload_as_str)


if __name__ == "__main__":
    main()

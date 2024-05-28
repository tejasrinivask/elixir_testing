import json
import sys

import requests

# TODO: update payload data with user provided data

custom_field_key_2_jira_key_map = {
    "Changed Component Name, In case code change is needed": "component",
    "What are the steps to reproduce this issue?": "stepstoreproduce",
    "Are there any features likely to be impacted? If so, what are the features and what is impact?": "impacts",
}


class Jira:

    def __init__(self, token):
        self.token = token
        self.url = "https://amagiengg.atlassian.net/rest/api/latest/issue"
        # self.default_payload = {
        #     "fields": {
        #         "customfield_12090": "||Changed Component Name, In case code change is needed| |\n||What are the steps to reproduce this issue?| |\n||Are there any features likely to be impacted? If so, what are the features and what is impact?| |\n||How can this change be tested? Is there any additional tests to be done other than bug fix validation?| |\n||Should this fix be considered for LTS Release?| Yes / No | |\n||Is the fix for this issue available in any of the latest CP releases?| |",
        #     }
        # }
        self.default_payload = {
            "fields": {
                "customfield_12562": "||Changed Component Name, In case code change is needed| |\n||What are the steps to reproduce this issue?| |\n||Are there any features likely to be impacted? If so, what are the features and what is impact?| |\n||How can this change be tested? Is there any additional tests to be done other than bug fix validation?| |\n||Should this fix be considered for LTS Release?| Yes / No | |\n||Is the fix for this issue available in any of the latest CP releases?| |",
            }
        }

    def get(self, issue_key):
        url = f"{self.url}/{issue_key}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.token}",
        }
        # Send GET request
        response = requests.get(url, headers=headers)
        if (
            response.status_code != 200
        ):  # issue doesn't exist or api key doesn't have permissions
            return {}
            # return False, ""
        response_data = response.json()
        return response_data

    def put(self, issue_key, payload):
        url = f"{self.url}/{issue_key}"
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.token}",
        }
        payload = {
            "fields": {
                "customfield_12562": payload,
            }
        }
        # print(payload)
        # Send the PUT request
        response = requests.put(url, headers=headers, data=json.dumps(payload))
        # Check response status
        if response.status_code == 204:
            print("Custom field updated successfully")
        else:
            print(
                f"Failed to update custom field. Status code: {response.status_code}, Error: {response.text}"
            )

    def payload_str_to_dict(
        self, payload_data, pr_data
    ):  # returns dict of payload_data
        if not payload_data:
            payload_data = self.default_payload["fields"]["customfield_12562"]
        payload_data_dict = self.jira_custom_field_to_dict(payload_data)
        for k, v in custom_field_key_2_jira_key_map.items():
            # print(k, v)
            if k in payload_data_dict:
                payload_data_dict[k].append(pr_data[v])
        return payload_data_dict

    def jira_custom_field_to_dict(self, custom_field_data):
        # print(f"custom_field_data -> {custom_field_data}")
        custom_field_dict = {}
        rows = custom_field_data.strip().split("\n")
        for row in rows:
            columns = row.split("|")
            key = columns[2].strip()  # First column is the key
            value = columns[3].strip()  # Rest of the columns are values
            if not value:
                custom_field_dict[key] = []
            else:
                custom_field_dict[key] = [value]
        return custom_field_dict

    def reconstruct_jira_payload_from_dict_to_str(self, custom_field_dict):
        payload_str = ""
        for k, v in custom_field_dict.items():
            payload_str = f"{payload_str}|| {k} | {', '.join(v)} |\n"
        return payload_str


def main():
    token = sys.argv[1]  # Jira account API key
    issue_key = sys.argv[2]  # Jira ID
    jira = Jira(token)
    # issue_exists, current_custom_field_data = jira.get(issue_key)
    response_data = jira.get(issue_key)
    # print(response_data)
    if not response_data:
        print(
            f"Jira issue: {issue_key} does not exist or user doesn't have permissions to access the issue"
        )
        sys.exit(1)
    try:
        # current_payload = response_data["fields"]["customfield_12090"]
        current_payload = response_data["fields"]["customfield_12562"]
        # print(f"current_payload -> {current_payload}")
    except Exception as err:  # doesn't have the required custom field
        current_payload = ""
    data_to_be_updated = {
        "JiraID": "DLP-1196",
        "pr": "262",
        "type": "feature",
        "component": "elixir",
        "description": "added feat3",
        "stepstoreproduce": "1. step1<br>2. step2",
        "impacts": "impacts componentx",
    }
    payload_dict = jira.payload_str_to_dict(current_payload, data_to_be_updated)
    # print(payload_dict)
    payload_as_str = jira.reconstruct_jira_payload_from_dict_to_str(payload_dict)
    # print(payload_as_str)
    jira.put(issue_key, payload=payload_as_str)


if __name__ == "__main__":
    main()

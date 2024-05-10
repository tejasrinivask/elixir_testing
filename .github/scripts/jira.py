import json
import requests
import sys


class Jira():

    def __init__(self, token):
        self.token = token
        self.url = 'https://amagiengg.atlassian.net/rest/api/latest/issue'
        self.default_payload = {
                "fields": {
                    "customfield_12090": "||Changed Component Name, In case code change is needed| |\n||What are the steps to reproduce this issue?| |\n||Are there any features likely to be impacted? If so, what are the features and what is impact?| |\n||How can this change be tested? Is there any additional tests to be done other than bug fix validation?| |\n||Should this fix be considered for LTS Release?| Yes / No | |\n||Is the fix for this issue available in any of the latest CP releases?| |",
                    }
                }

    def get(self, issue_key):
        url = f'{self.url}/{issue_key}'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self.token}'
        }
        # Send GET request
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return False, ""
        response_data = response.json()
        try:
            current_payload = response_data['fields']['customfield_12090']
        except Exception as err:
            print(f'Issue getting table for {issue_key}, error: {err}')
            return True, ""
        return True, current_payload

    def put(self, issue_key, payload):
        url = f'{self.url}/{issue_key}'
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self.token}'
        }
        payload = {
                "fields": {
                    "customfield_12090": payload,
                    }
                }
        # Send the PUT request
        response = requests.put(url, headers=headers, data=json.dumps(payload))
        # Check response status
        if response.status_code == 204:
            print("Custom field updated successfully")
        else:
            print(f"Failed to update custom field. Status code: {response.status_code}, Error: {response.text}")

    def generate_jira_payload(self, data):
        if not data:
            return self.jira_custom_field_to_dict(self.default_payload)
        else:
            return self.jira_custom_field_to_dict(data)

    def jira_custom_field_to_dict(self, custom_field_data):
        custom_field_dict = {}
        rows = custom_field_data.strip().split('\n')
        for row in rows:
            columns = row.split('|')
            key = columns[2].strip()  # First column is the key
            value = columns[3].strip()  # Rest of the columns are values
            custom_field_dict[key] = [value]
        return custom_field_dict

def main():
    token = sys.argv[1]
    issue_key = sys.argv[2]
    jira = Jira(token)
    issue_exists, current_custom_field_data = jira.get(issue_key)
    if not issue_exists:
        print(f"Jira issue: {issue_key} does not exist")
        sys.exit(1)
    jira_payload_data = jira.generate_jira_payload(current_custom_field_data)
    # print(jira_payload_data)
    jira.put(issue_key, payload=jira_payload_data)


if __name__ == '__main__':
    main()

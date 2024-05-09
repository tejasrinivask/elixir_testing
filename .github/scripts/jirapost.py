# Basic authentication GET
# import requests
#
# token = 'api_token'
# # Set the URL and headers
# url = 'https://amagiengg.atlassian.net/rest/api/latest/issue/PIE-3983'
# headers = {
#     'Content-Type': 'application/json',
#     'Authorization': f'Basic {token}'
# }
#
# # Send GET request
# response = requests.get(url, headers=headers)
#
# # Print response
# print(response.text)

# Basic authentication PUT
import requests
import json

# Authentication details
token = 'api_token'

# Endpoint URL for updating the custom field of an issue
issue_key = 'PIE-3983'
url = f'https://amagiengg.atlassian.net/rest/api/latest/issue/{issue_key}'

# Prepare headers
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Basic {token}'
}

payload = {
        "fields": {
            "customfield_12090": "||Changed Component Name, In case code change is needed| cp-build-automation |\n||What are the steps to reproduce this issue?| |\n||Are there any features likely to be impacted? If so, what are the features and what is impact?| |\n||How can this change be tested? Is there any additional tests to be done other than bug fix validation?| |\n||Should this fix be considered for LTS Release?| No | |\n||Is the fix for this issue available  in any of the latest CP releases?| |",

            }
        }
# Send the PUT request
response = requests.put(url, headers=headers, data=json.dumps(payload))

# Check response status
if response.status_code == 204:
    print("Custom field updated successfully")
else:
    print(f"Failed to update custom field. Status code: {response.status_code}, Error: {response.text}")


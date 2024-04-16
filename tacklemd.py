import re
import yaml

def markdown_tables_to_dicts(markdown_text):
    tables = {}
    current_table = None
    lines = markdown_text.strip().split('\n')

    for line in lines:
        if re.match(r'^#+\s+\w+', line):  # Check for headings
            current_table = None
            table_name = line.strip('#').strip()
            if table_name not in tables:
                tables[table_name] = {}
            current_table = tables[table_name]
        elif re.match(r'^\|.*\|$', line):  # Check for table rows
            if current_table is not None:
                if 'headers' not in current_table:
                    current_table['headers'] = [header.strip() for header in line.strip('|').split('|') if header.strip()]
                    current_table['data'] = []
                else:
                    row_data = [data.strip() for data in line.strip('|').split('|')]
                    if current_table['data'] or any(cell.strip() for cell in row_data):
                        current_table['data'].append(dict(zip(current_table['headers'], row_data)))

    # Remove the first data entry (separator row) from each table
    for table in tables.values():
        if table.get('data'):
            del table['data'][0]

    return tables

# Example Markdown text
markdown_text = """
### Changes
| Jira ID | Description |
| --- | --- |
| DLP-485 | Changes for simulcast templates. |
| CRP-1034 | Mount point for S3 playout |
| CRP-1299 | Changes to support srt1.5 in helm and sdc. |

### Config Changes
#### New Configs
| file | keyPath | description | mandatory | type | allowed-value | default-value | sample-value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | |

#### Removed Configs
| file | keyPath | description |
| --- | --- | --- |
| | | |

#### Deprecated Configs
| file | keyPath | description |
| --- | --- | --- |
| | | |

### Dependencies
| Dependency |
| --- |
| | |

### Limitations
| Limitations |
| --- |
| | |

### Deprecated Features
| Deprecated Features |
| --- |
| | |
"""

# Convert Markdown tables to dictionaries
result = markdown_tables_to_dicts(markdown_text)
print(result)

# Format the dictionaries into YAML
yaml_output = yaml.dump(result, default_flow_style=False)
print(yaml_output)

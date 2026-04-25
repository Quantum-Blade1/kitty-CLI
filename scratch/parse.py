import json

with open('c:/start/bandit_report.json', 'r') as f:
    data = json.load(f)

for result in data.get('results', []):
    if result.get('issue_severity') in ('HIGH', 'MEDIUM'):
        print(f"{result['filename']}:{result['line_number']} - {result['issue_severity']}: {result['issue_text']}")

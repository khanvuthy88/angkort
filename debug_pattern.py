#!/usr/bin/env python3
"""
Debug script to understand the exact string format
"""

import re

# Test the exact pattern from the file
test_line = "return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')"

print("Test line:", repr(test_line))
print("Length:", len(test_line))

# Try different patterns
patterns = [
    r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\)',
    r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\)',
    r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\)',
    r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\)',
]

for i, pattern in enumerate(patterns):
    print(f"\nPattern {i+1}:", repr(pattern))
    match = re.search(pattern, test_line)
    if match:
        print("Match found!")
        print("Groups:", match.groups())
    else:
        print("No match")

# Try to find the exact substring
print(f"\nLooking for 'Response(' in test line: {'Response(' in test_line}")
print(f"Looking for 'json.dumps(' in test line: {'json.dumps(' in test_line}")
print(f"Looking for 'error' in test line: {'error' in test_line}")

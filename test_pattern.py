#!/usr/bin/env python3
"""
Test script to verify regex pattern matching
"""

import re

# Test the exact pattern from the file
test_line = "return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')"

# Pattern to match
pattern = r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\), status=(\d+), content_type=\'application/json\''

print("Test line:", test_line)
print("Pattern:", pattern)
print("Match found:", bool(re.match(pattern, test_line)))

# Try to find the match
match = re.search(pattern, test_line)
if match:
    print("Groups:", match.groups())
else:
    print("No match found")

# Test with a simpler pattern
simple_pattern = r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\)'
print("\nSimple pattern:", simple_pattern)
print("Simple match found:", bool(re.search(simple_pattern, test_line)))

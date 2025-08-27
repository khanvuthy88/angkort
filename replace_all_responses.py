#!/usr/bin/env python3
"""
Comprehensive script to replace ALL remaining Response patterns with helper methods
"""

import re

def replace_all_responses():
    """Replace all remaining Response patterns with helper methods"""
    
    # Read the file
    with open('e_menu/controllers/shop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count initial patterns
    initial_count = len(re.findall(r'return Response\(json\.dumps\(\{', content))
    print(f"Initial Response patterns found: {initial_count}")
    
    # Pattern 1: Simple error responses with 'error' field
    pattern1 = r'return Response\(json\.dumps\(\{\'error\': \'([^\']+)\'\}\)\), status=(\d+), content_type=\'application/json\''
    replacement1 = r'return self._create_error_response(\n                message="\1",\n                status_code="\2",\n                http_status=\2\n            )'
    
    # Pattern 2: Error with str(e)
    pattern2 = r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\), status=(\d+), content_type=\'application/json\''
    replacement2 = r'return self._create_error_response(\n                message="An error occurred",\n                status_code="\1",\n                errors=[{"name": "general", "message": str(e)}],\n                http_status=\1\n            )'
    
    # Pattern 3: Success with message
    pattern3 = r'return Response\(json\.dumps\(\{\'message\': ([^}]+)\}\)\), status=(\d+), content_type=\'application/json\''
    replacement3 = r'return self._create_success_response(\n                message=\1,\n                http_status=\2\n            )'
    
    # Pattern 4: Success with data only
    pattern4 = r'return Response\(json\.dumps\(([^)]+)\)\), status=(\d+), content_type=\'application/json\''
    replacement4 = r'return self._create_success_response(\n                data=\1,\n                http_status=\2\n            )'
    
    # Pattern 5: Complex error responses with status, message, statusCode, errors
    pattern5 = r'return Response\(json\.dumps\(\{\s*"status": "error",\s*"message": "([^"]+)",\s*"statusCode": "([^"]+)",\s*"errors": (\[[^\]]+\])\s*\}\)\), status=(\d+), content_type=\'application/json\''
    replacement5 = r'return self._create_error_response(\n                message="\1",\n                status_code="\2",\n                errors=\3,\n                http_status=\4\n            )'
    
    # Pattern 6: Complex success responses with status, message, statusCode
    pattern6 = r'return Response\(json\.dumps\(\{\s*"status": "success",\s*"message": "([^"]+)",\s*"statusCode": "([^"]+)"\s*\}\)\), status=(\d+), content_type=\'application/json\''
    replacement6 = r'return self._create_success_response(\n                message="\1",\n                status_code="\2",\n                http_status=\3\n            )'
    
    # Pattern 7: Complex success responses with status, message, statusCode, data
    pattern7 = r'return Response\(json\.dumps\(\{\s*"status": "success",\s*"message": "([^"]+)",\s*"statusCode": "([^"]+)",\s*"data": ([^}]+)\s*\}\)\), status=(\d+), content_type=\'application/json\''
    replacement7 = r'return self._create_success_response(\n                data=\3,\n                message="\1",\n                status_code="\2",\n                http_status=\4\n            )'
    
    # Pattern 8: Complex error responses with status, message, statusCode (no errors field)
    pattern8 = r'return Response\(json\.dumps\(\{\s*"status": "error",\s*"message": "([^"]+)",\s*"statusCode": "([^"]+)"\s*\}\)\), status=(\d+), content_type=\'application/json\''
    replacement8 = r'return self._create_error_response(\n                message="\1",\n                status_code="\2",\n                http_status=\3\n            )'
    
    # Apply all replacements
    patterns = [
        (pattern1, replacement1),
        (pattern2, replacement2),
        (pattern3, replacement3),
        (pattern4, replacement4),
        (pattern5, replacement5),
        (pattern6, replacement6),
        (pattern7, replacement7),
        (pattern8, replacement8),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Count remaining patterns
    remaining_count = len(re.findall(r'return Response\(json\.dumps\(\{', content))
    print(f"Remaining Response patterns: {remaining_count}")
    print(f"Patterns replaced: {initial_count - remaining_count}")
    
    # Write the optimized content back
    with open('e_menu/controllers/shop.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("All Response patterns have been replaced with helper methods!")
    
    if remaining_count > 0:
        print(f"\nWarning: {remaining_count} patterns still remain and may need manual review.")
        print("These might be complex patterns that require individual attention.")

if __name__ == "__main__":
    replace_all_responses()

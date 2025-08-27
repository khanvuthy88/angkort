#!/usr/bin/env python3
"""
Final optimization script to replace ALL remaining Response patterns in shop.py controller
"""

import re

def final_optimization():
    """Replace ALL remaining repetitive Response patterns with helper methods"""
    
    # Read the file
    with open('e_menu/controllers/shop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count initial patterns
    initial_count = len(re.findall(r'return Response\(json\.dumps\(\{', content))
    print(f"Initial Response patterns found: {initial_count}")
    
    # Pattern 1: Replace all remaining simple error patterns
    patterns_to_replace = [
        # Simple error responses
        (r'return Response\(json\.dumps\(\{\'error\': \'([^\']+)\'\}\)\), status=(\d+), content_type=\'application/json\'',
         r'return self._create_error_response(\n                message="\1",\n                status_code="\2",\n                http_status=\2\n            )'),
        
        # Error with str(e)
        (r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\), status=(\d+), content_type=\'application/json\'',
         r'return self._create_error_response(\n                message="An error occurred",\n                status_code="\1",\n                errors=[{"name": "general", "message": str(e)}],\n                http_status=\1\n            )'),
        
        # Success with message
        (r'return Response\(json\.dumps\(\{\'message\': ([^}]+)\}\)\), status=(\d+), content_type=\'application/json\'',
         r'return self._create_success_response(\n                message=\1,\n                http_status=\2\n            )'),
        
        # Success with data only
        (r'return Response\(json\.dumps\(([^)]+)\)\), status=(\d+), content_type=\'application/json\'',
         r'return self._create_success_response(\n                data=\1,\n                http_status=\2\n            )'),
        
        # Complex error responses with status, message, statusCode, errors
        (r'return Response\(json\.dumps\(\{\s*"status": "error",\s*"message": "([^"]+)",\s*"statusCode": "([^"]+)",\s*"errors": (\[[^\]]+\])\s*\}\)\), status=(\d+), content_type=\'application/json\'',
         r'return self._create_error_response(\n                message="\1",\n                status_code="\2",\n                errors=\3,\n                http_status=\4\n            )'),
        
        # Complex success responses with status, message, statusCode
        (r'return Response\(json\.dumps\(\{\s*"status": "success",\s*"message": "([^"]+)",\s*"statusCode": "([^"]+)"\s*\}\)\), status=(\d+), content_type=\'application/json\'',
         r'return self._create_success_response(\n                message="\1",\n                status_code="\2",\n                http_status=\3\n            )'),
        
        # Complex success responses with status, message, statusCode, data
        (r'return Response\(json\.dumps\(\{\s*"status": "success",\s*"message": "([^"]+)",\s*"statusCode": "([^"]+)",\s*"data": ([^}]+)\s*\}\)\), status=(\d+), content_type=\'application/json\'',
         r'return self._create_success_response(\n                data=\3,\n                message="\1",\n                status_code="\2",\n                http_status=\4\n            )'),
    ]
    
    # Apply all patterns
    for pattern, replacement in patterns_to_replace:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Count remaining patterns
    remaining_count = len(re.findall(r'return Response\(json\.dumps\(\{', content))
    print(f"Remaining Response patterns: {remaining_count}")
    print(f"Patterns replaced: {initial_count - remaining_count}")
    
    # Write the optimized content back
    with open('e_menu/controllers/shop.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Final optimization completed!")
    
    if remaining_count > 0:
        print(f"\nWarning: {remaining_count} patterns still remain and may need manual review.")
        print("These might be complex patterns that require individual attention.")

if __name__ == "__main__":
    final_optimization()

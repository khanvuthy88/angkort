#!/usr/bin/env python3
"""
Corrected optimization script to replace Response patterns with proper quote handling
"""

import re

def corrected_optimization():
    """Replace Response patterns with proper quote handling"""
    
    # Read the file
    with open('e_menu/controllers/shop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count initial patterns
    initial_count = len(re.findall(r'return Response\(json\.dumps\(\{', content))
    print(f"Initial Response patterns found: {initial_count}")
    
    # Pattern 1: Simple error responses with single quotes
    pattern1 = r'return Response\(json\.dumps\(\{\'error\': \'([^\']+)\'\}\)\), status=(\d+), content_type=\'application/json\''
    replacement1 = r'return self._create_error_response(\n                message="\1",\n                status_code="\2",\n                http_status=\2\n            )'
    
    # Pattern 2: Error with str(e) and single quotes
    pattern2 = r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\), status=(\d+), content_type=\'application/json\''
    replacement2 = r'return self._create_error_response(\n                message="An error occurred",\n                status_code="\1",\n                errors=[{"name": "general", "message": str(e)}],\n                http_status=\1\n            )'
    
    # Pattern 3: Success with message and single quotes
    pattern3 = r'return Response\(json\.dumps\(\{\'message\': ([^}]+)\}\)\), status=(\d+), content_type=\'application/json\''
    replacement3 = r'return self._create_success_response(\n                message=\1,\n                http_status=\2\n            )'
    
    # Pattern 4: Success with data only and single quotes
    pattern4 = r'return Response\(json\.dumps\(([^)]+)\)\), status=(\d+), content_type=\'application/json\''
    replacement4 = r'return self._create_success_response(\n                data=\1,\n                http_status=\2\n            )'
    
    # Apply replacements
    content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(pattern3, replacement3, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(pattern4, replacement4, content, flags=re.MULTILINE | re.DOTALL)
    
    # Count remaining patterns
    remaining_count = len(re.findall(r'return Response\(json\.dumps\(\{', content))
    print(f"Remaining Response patterns: {remaining_count}")
    print(f"Patterns replaced: {initial_count - remaining_count}")
    
    # Write the optimized content back
    with open('e_menu/controllers/shop.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Corrected optimization completed!")

if __name__ == "__main__":
    corrected_optimization()

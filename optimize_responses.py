#!/usr/bin/env python3
"""
Script to optimize repetitive Response patterns in shop.py controller
"""

import re

def optimize_responses():
    """Replace repetitive Response patterns with helper methods"""
    
    # Read the file
    with open('e_menu/controllers/shop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern 1: Error responses with status, message, statusCode, errors
    error_pattern = r'return Response\(json\.dumps\(\{\s*"status": "error",\s*"message": "([^"]+)",\s*"statusCode": "([^"]+)",\s*"errors": (\[[^\]]+\])\s*\}\)\), status=(\d+), content_type=\'application/json\''
    error_replacement = r'return self._create_error_response(\n                message="\1",\n                status_code="\2",\n                errors=\3,\n                http_status=\4\n            )'
    
    # Pattern 2: Simple error responses with just error message
    simple_error_pattern = r'return Response\(json\.dumps\(\{\'error\': \'([^\']+)\'\}\)\), status=(\d+), content_type=\'application/json\''
    simple_error_replacement = r'return self._create_error_response(\n                message="\1",\n                status_code="\2",\n                http_status=\2\n            )'
    
    # Pattern 3: Success responses with message only
    success_message_pattern = r'return Response\(json\.dumps\(\{\'message\': ([^}]+)\}\)\), status=(\d+), content_type=\'application/json\''
    success_message_replacement = r'return self._create_success_response(\n                message=\1,\n                http_status=\2\n            )'
    
    # Pattern 4: Success responses with data
    success_data_pattern = r'return Response\(json\.dumps\(([^)]+)\)\), status=(\d+), content_type=\'application/json\''
    success_data_replacement = r'return self._create_success_response(\n                data=\1,\n                http_status=\2\n            )'
    
    # Apply replacements
    content = re.sub(error_pattern, error_replacement, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(simple_error_pattern, simple_error_replacement, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(success_message_pattern, success_message_replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # More specific patterns for common cases
    # Shop not found pattern
    shop_not_found_pattern = r'return Response\(json\.dumps\(\{\s*"status": "error",\s*"message": "([^"]+)",\s*"statusCode": "404",\s*"errors": \[{"name": "shop_id", "message": "Shop not found"}\]\s*\}\)\), status=404, content_type=\'application/json\''
    shop_not_found_replacement = r'return self._create_error_response(\n                message="\1",\n                status_code="404",\n                errors=[{"name": "shop_id", "message": "Shop not found"}],\n                http_status=404\n            )'
    
    # General exception pattern
    general_exception_pattern = r'return Response\(json\.dumps\(\{\s*"status": "error",\s*"message": "([^"]+)",\s*"statusCode": "500",\s*"errors": \[{"name": "general", "message": str\(e\)}\]\s*\}\)\), status=500, content_type=\'application/json\''
    general_exception_replacement = r'return self._create_error_response(\n                message="\1",\n                status_code="500",\n                errors=[{"name": "general", "message": str(e)}],\n                http_status=500\n            )'
    
    # Apply specific patterns
    content = re.sub(shop_not_found_pattern, shop_not_found_replacement, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(general_exception_pattern, general_exception_replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Write the optimized content back
    with open('e_menu/controllers/shop.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Response optimization completed!")
    print("Note: Some patterns may need manual review and adjustment.")

if __name__ == "__main__":
    optimize_responses()

#!/usr/bin/env python3
"""
Comprehensive script to optimize all repetitive Response patterns in shop.py controller
"""

import re

def optimize_responses_v2():
    """Replace all remaining repetitive Response patterns with helper methods"""
    
    # Read the file
    with open('e_menu/controllers/shop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern 1: Simple error responses with just 'error' field
    simple_error_pattern = r'return Response\(json\.dumps\(\{\'error\': \'([^\']+)\'\}\)\), status=(\d+), content_type=\'application/json\''
    simple_error_replacement = r'return self._create_error_response(\n                message="\1",\n                status_code="\2",\n                http_status=\2\n            )'
    
    # Pattern 2: Error responses with 'error' field and str(e)
    error_str_pattern = r'return Response\(json\.dumps\(\{\'error\': str\(e\)\}\)\), status=(\d+), content_type=\'application/json\''
    error_str_replacement = r'return self._create_error_response(\n                message="An error occurred",\n                status_code="\1",\n                errors=[{"name": "general", "message": str(e)}],\n                http_status=\1\n            )'
    
    # Pattern 3: Success responses with just 'message' field
    success_message_pattern = r'return Response\(json\.dumps\(\{\'message\': ([^}]+)\}\)\), status=(\d+), content_type=\'application/json\''
    success_message_replacement = r'return self._create_success_response(\n                message=\1,\n                http_status=\2\n            )'
    
    # Pattern 4: Success responses with data only
    success_data_pattern = r'return Response\(json\.dumps\(([^)]+)\)\), status=(\d+), content_type=\'application/json\''
    success_data_replacement = r'return self._create_success_response(\n                data=\1,\n                http_status=\2\n            )'
    
    # Pattern 5: Shop not found errors
    shop_not_found_pattern = r'return Response\(json\.dumps\(\{\'error\': \'Shop not found\'\}\)\), status=404, content_type=\'application/json\''
    shop_not_found_replacement = r'return self._create_error_response(\n                message="Shop not found",\n                status_code="404",\n                http_status=404\n            )'
    
    # Pattern 6: Product not found errors
    product_not_found_pattern = r'return Response\(json\.dumps\(\{\'error\': \'Product not found\'\}\)\), status=404, content_type=\'application/json\''
    product_not_found_replacement = r'return self._create_error_response(\n                message="Product not found",\n                status_code="404",\n                http_status=404\n            )'
    
    # Pattern 7: Attribute not found errors
    attribute_not_found_pattern = r'return Response\(json\.dumps\(\{\'error\': \'Attribute not found\'\}\)\), status=404, content_type=\'application/json\''
    attribute_not_found_replacement = r'return self._create_error_response(\n                message="Attribute not found",\n                status_code="404",\n                http_status=404\n            )'
    
    # Pattern 8: Specific success messages
    specific_success_patterns = [
        (r'return Response\(json\.dumps\(\{\'message\': \'Attribute values created successfully\'\}\)\), status=201, content_type=\'application/json\'',
         r'return self._create_success_response(\n                message="Attribute values created successfully",\n                status_code="201",\n                http_status=201\n            )'),
        (r'return Response\(json\.dumps\(\{\'message\': \'Variant value updated successfully\'\}\)\), status=200, content_type=\'application/json\'',
         r'return self._create_success_response(\n                message="Variant value updated successfully",\n                http_status=200\n            )'),
        (r'return Response\(json\.dumps\(\{\'message\': \'Variant value patched successfully\'\}\)\), status=200, content_type=\'application/json\'',
         r'return self._create_success_response(\n                message="Variant value patched successfully",\n                http_status=200\n            )'),
    ]
    
    # Apply all replacements
    content = re.sub(simple_error_pattern, simple_error_replacement, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(error_str_pattern, error_str_replacement, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(success_message_pattern, success_message_replacement, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(success_data_pattern, success_data_replacement, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(shop_not_found_pattern, shop_not_found_replacement, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(product_not_found_pattern, product_not_found_replacement, content, flags=re.MULTILINE | re.DOTALL)
    content = re.sub(attribute_not_found_pattern, attribute_not_found_replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Apply specific success patterns
    for pattern, replacement in specific_success_patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Write the optimized content back
    with open('e_menu/controllers/shop.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Comprehensive response optimization completed!")
    print("All major repetitive patterns have been replaced with helper methods.")

if __name__ == "__main__":
    optimize_responses_v2()

#!/usr/bin/env python3
"""
Script to standardize all update operation responses to match create operation structure
"""

def standardize_responses():
    """Standardize all update operation responses to match create operation structure"""
    
    # Read the file
    with open('e_menu/controllers/shop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define the patterns to replace
    replacements = [
        # Simple message responses that should be standardized
        (
            r'return Response\(json\.dumps\(\{\'message\': \'Variant value updated successfully\'\}\)\), status=200, content_type=\'application/json\'',
            r'return Response(json.dumps({\n                "status": "success",\n                "message": "Variant value updated successfully",\n                "statusCode": "200"\n            }), status=200, content_type=\'application/json\')'
        ),
        (
            r'return Response\(json\.dumps\(\{\'message\': \'Variant value patched successfully\'\}\)\), status=200, content_type=\'application/json\'',
            r'return Response(json.dumps({\n                "status": "success",\n                "message": "Variant value patched successfully",\n                "statusCode": "200"\n            }), status=200, content_type=\'application/json\')'
        ),
        (
            r'return Response\(json\.dumps\(\{\'message\': \'Attribute values created successfully\'\}\)\), status=201, content_type=\'application/json\'',
            r'return Response(json.dumps({\n                "status": "success",\n                "message": "Attribute values created successfully",\n                "statusCode": "201"\n            }), status=201, content_type=\'application/json\')'
        ),
        # Add more patterns as needed
    ]
    
    # Apply all replacements
    for old_pattern, new_pattern in replacements:
        content = content.replace(old_pattern, new_pattern)
    
    # Write the updated content back
    with open('e_menu/controllers/shop.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Response standardization completed!")

if __name__ == "__main__":
    standardize_responses()

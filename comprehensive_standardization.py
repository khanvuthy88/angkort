#!/usr/bin/env python3
"""
Comprehensive script to standardize all remaining simple message responses
"""

def comprehensive_standardization():
    """Standardize all remaining simple message responses"""
    
    # Read the file
    with open('e_menu/controllers/shop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define all the patterns to replace
    replacements = [
        # Shop update success response
        (
            r'return Response\(json\.dumps\(\{\'message\': f\'Shop with ID \{shop_id\} updated successfully\'\}\)\), status=200, content_type=\'application/json\'',
            r'return Response(json.dumps({\n                "status": "success",\n                "message": f"Shop with ID {shop_id} updated successfully",\n                "statusCode": "200"\n            }), status=200, content_type=\'application/json\')'
        ),
        # Attribute values created successfully (201)
        (
            r'return Response\(json\.dumps\(\{\'message\': \'Attribute values created successfully\'\}\)\), status=201, content_type=\'application/json\'',
            r'return Response(json.dumps({\n                "status": "success",\n                "message": "Attribute values created successfully",\n                "statusCode": "201"\n            }), status=201, content_type=\'application/json\')'
        ),
        # Variant value updated successfully (200)
        (
            r'return Response\(json\.dumps\(\{\'message\': \'Variant value updated successfully\'\}\)\), status=200, content_type=\'application/json\'',
            r'return Response(json.dumps({\n                "status": "success",\n                "message": "Variant value updated successfully",\n                "statusCode": "200"\n            }), status=200, content_type=\'application/json\')'
        ),
        # Variant value patched successfully (200)
        (
            r'return Response\(json\.dumps\(\{\'message\': \'Variant value patched successfully\'\}\)\), status=200, content_type=\'application/json\'',
            r'return Response(json.dumps({\n                "status": "success",\n                "message": "Variant value patched successfully",\n                "statusCode": "200"\n            }), status=200, content_type=\'application/json\')'
        ),
    ]
    
    # Apply all replacements
    for old_pattern, new_pattern in replacements:
        content = content.replace(old_pattern, new_pattern)
    
    # Write the updated content back
    with open('e_menu/controllers/shop.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Comprehensive response standardization completed!")

if __name__ == "__main__":
    comprehensive_standardization()

#!/usr/bin/env python3
"""
Targeted replacement script for specific Response patterns found in the file
"""

def targeted_replacement():
    """Replace specific Response patterns with helper methods"""
    
    # Read the file
    with open('e_menu/controllers/shop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count initial patterns
    initial_count = content.count('return Response(json.dumps({')
    print(f"Initial Response patterns found: {initial_count}")
    
    # Replace specific patterns one by one
    
    # Pattern 1: Simple error with str(e)
    old_pattern1 = "return Response(json.dumps({'error': str(e)}), status=500, content_type='application/json')"
    new_pattern1 = """            return self._create_error_response(
                message="An error occurred",
                status_code="500",
                errors=[{"name": "general", "message": str(e)}],
                http_status=500
            )"""
    content = content.replace(old_pattern1, new_pattern1)
    
    # Pattern 2: Simple error with 'Shop not found'
    old_pattern2 = "return Response(json.dumps({'error': 'Shop not found'}), status=404, content_type='application/json')"
    new_pattern2 = """            return self._create_error_response(
                message="Shop not found",
                status_code="404",
                http_status=404
            )"""
    content = content.replace(old_pattern2, new_pattern2)
    
    # Pattern 3: Simple error with 'Product not found'
    old_pattern3 = "return Response(json.dumps({'error': 'Product not found'}), status=404, content_type='application/json')"
    new_pattern3 = """            return self._create_error_response(
                message="Product not found",
                status_code="404",
                http_status=404
            )"""
    content = content.replace(old_pattern3, new_pattern3)
    
    # Pattern 4: Simple error with 'Attribute not found'
    old_pattern4 = "return Response(json.dumps({'error': 'Attribute not found'}), status=404, content_type='application/json')"
    new_pattern4 = """            return self._create_error_response(
                message="Attribute not found",
                status_code="404",
                http_status=404
            )"""
    content = content.replace(old_pattern4, new_pattern4)
    
    # Pattern 5: Success with message 'Attribute values created successfully'
    old_pattern5 = "return Response(json.dumps({'message': 'Attribute values created successfully'}), status=201, content_type='application/json')"
    new_pattern5 = """            return self._create_success_response(
                message="Attribute values created successfully",
                status_code="201",
                http_status=201
            )"""
    content = content.replace(old_pattern5, new_pattern5)
    
    # Pattern 6: Success with message 'Variant value updated successfully'
    old_pattern6 = "return Response(json.dumps({'message': 'Variant value updated successfully'}), status=200, content_type='application/json')"
    new_pattern6 = """            return self._create_success_response(
                message="Variant value updated successfully",
                http_status=200
            )"""
    content = content.replace(old_pattern6, new_pattern6)
    
    # Pattern 7: Success with message 'Variant value patched successfully'
    old_pattern7 = "return Response(json.dumps({'message': 'Variant value patched successfully'}), status=200, content_type='application/json')"
    new_pattern7 = """            return self._create_success_response(
                message="Variant value patched successfully",
                http_status=200
            )"""
    content = content.replace(old_pattern7, new_pattern7)
    
    # Pattern 8: Success with message 'Shop with ID {shop_id} updated successfully'
    old_pattern8 = "return Response(json.dumps({'message': f'Shop with ID {shop_id} updated successfully'}), status=200, content_type='application/json')"
    new_pattern8 = """            return self._create_success_response(
                message=f'Shop with ID {shop_id} updated successfully',
                http_status=200
            )"""
    content = content.replace(old_pattern8, new_pattern8)
    
    # Count remaining patterns
    remaining_count = content.count('return Response(json.dumps({')
    print(f"Remaining Response patterns: {remaining_count}")
    print(f"Patterns replaced: {initial_count - remaining_count}")
    
    # Write the optimized content back
    with open('e_menu/controllers/shop.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Targeted replacement completed!")
    
    if remaining_count > 0:
        print(f"\n{remaining_count} patterns still remain. These may need manual review.")

if __name__ == "__main__":
    targeted_replacement()

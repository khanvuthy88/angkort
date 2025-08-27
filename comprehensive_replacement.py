#!/usr/bin/env python3
"""
Comprehensive replacement script that handles all remaining Response patterns
"""

def comprehensive_replacement():
    """Replace all remaining Response patterns with helper methods"""
    
    # Read the file
    with open('e_menu/controllers/shop.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count initial patterns
    initial_count = content.count('return Response(json.dumps({')
    print(f"Initial Response patterns found: {initial_count}")
    
    # Find all Response patterns and replace them systematically
    lines = content.split('\n')
    new_lines = []
    replacements_made = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if 'return Response(json.dumps({' in line:
            # This is a Response line, let's analyze it
            response_start = i
            response_end = i
            
            # Find the complete Response block
            brace_count = 0
            in_string = False
            string_char = None
            
            for j in range(i, len(lines)):
                current_line = lines[j]
                
                for char in current_line:
                    if char in ['"', "'"] and (not in_string or char == string_char):
                        if not in_string:
                            in_string = True
                            string_char = char
                        else:
                            in_string = False
                            string_char = None
                    elif not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                response_end = j
                                break
                
                if response_end > i:
                    break
            
            # Extract the complete response block
            response_lines = lines[response_start:response_end + 1]
            response_text = '\n'.join(response_lines)
            
            # Analyze the response content and replace with appropriate helper
            if '"status": "error"' in response_text:
                if '"errors":' in response_text:
                    # Complex error response
                    new_response = create_error_response_from_text(response_text)
                else:
                    # Simple error response
                    new_response = create_simple_error_response_from_text(response_text)
            elif '"status": "success"' in response_text:
                if '"data":' in response_text:
                    # Success response with data
                    new_response = create_success_response_with_data_from_text(response_text)
                else:
                    # Success response with message only
                    new_response = create_success_response_from_text(response_text)
            else:
                # Simple response (no status field)
                new_response = create_simple_response_from_text(response_text)
            
            # Replace the response block
            new_lines.extend(new_response)
            replacements_made += 1
            
            # Skip the lines we just processed
            i = response_end + 1
        else:
            new_lines.append(line)
            i += 1
    
    # Write the updated content
    updated_content = '\n'.join(new_lines)
    
    with open('e_menu/controllers/shop.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    # Count remaining patterns
    remaining_count = updated_content.count('return Response(json.dumps({')
    print(f"Remaining Response patterns: {remaining_count}")
    print(f"Patterns replaced: {replacements_made}")
    
    print("Comprehensive replacement completed!")

def create_error_response_from_text(response_text):
    """Create error response helper method call from response text"""
    # Extract message, statusCode, and errors
    import re
    
    message_match = re.search(r'"message": "([^"]+)"', response_text)
    status_code_match = re.search(r'"statusCode": "([^"]+)"', response_text)
    errors_match = re.search(r'"errors": (\[[^\]]+\])', response_text)
    status_match = re.search(r'status=(\d+)', response_text)
    
    message = message_match.group(1) if message_match else "An error occurred"
    status_code = status_code_match.group(1) if status_code_match else "400"
    errors = errors_match.group(1) if errors_match else None
    http_status = status_match.group(1) if status_match else "400"
    
    if errors:
        return [
            f'            return self._create_error_response(',
            f'                message="{message}",',
            f'                status_code="{status_code}",',
            f'                errors={errors},',
            f'                http_status={http_status}',
            f'            )'
        ]
    else:
        return [
            f'            return self._create_error_response(',
            f'                message="{message}",',
            f'                status_code="{status_code}",',
            f'                http_status={http_status}',
            f'            )'
        ]

def create_simple_error_response_from_text(response_text):
    """Create simple error response helper method call"""
    import re
    
    message_match = re.search(r'"message": "([^"]+)"', response_text)
    status_code_match = re.search(r'"statusCode": "([^"]+)"', response_text)
    status_match = re.search(r'status=(\d+)', response_text)
    
    message = message_match.group(1) if message_match else "An error occurred"
    status_code = status_code_match.group(1) if status_code_match else "400"
    http_status = status_match.group(1) if status_match else "400"
    
    return [
        f'            return self._create_error_response(',
        f'                message="{message}",',
        f'                status_code="{status_code}",',
        f'                http_status={http_status}',
        f'            )'
    ]

def create_success_response_from_text(response_text):
    """Create success response helper method call"""
    import re
    
    message_match = re.search(r'"message": "([^"]+)"', response_text)
    status_code_match = re.search(r'"statusCode": "([^"]+)"', response_text)
    status_match = re.search(r'status=(\d+)', response_text)
    
    message = message_match.group(1) if message_match else ""
    status_code = status_code_match.group(1) if status_code_match else "200"
    http_status = status_match.group(1) if status_match else "200"
    
    return [
        f'            return self._create_success_response(',
        f'                message="{message}",',
        f'                status_code="{status_code}",',
        f'                http_status={http_status}',
        f'            )'
    ]

def create_success_response_with_data_from_text(response_text):
    """Create success response with data helper method call"""
    import re
    
    message_match = re.search(r'"message": "([^"]+)"', response_text)
    status_code_match = re.search(r'"statusCode": "([^"]+)"', response_text)
    data_match = re.search(r'"data": ([^}]+)', response_text)
    status_match = re.search(r'status=(\d+)', response_text)
    
    message = message_match.group(1) if message_match else ""
    status_code = status_code_match.group(1) if status_code_match else "200"
    data = data_match.group(1) if data_match else "None"
    http_status = status_match.group(1) if status_match else "200"
    
    return [
        f'            return self._create_success_response(',
        f'                data={data},',
        f'                message="{message}",',
        f'                status_code="{status_code}",',
        f'                http_status={http_status}',
        f'            )'
    ]

def create_simple_response_from_text(response_text):
    """Create simple response helper method call"""
    import re
    
    # Check if it's a simple data response
    if 'response' in response_text or 'data' in response_text:
        status_match = re.search(r'status=(\d+)', response_text)
        http_status = status_match.group(1) if status_match else "200"
        
        return [
            f'            return self._create_success_response(',
            f'                http_status={http_status}',
            f'            )'
        ]
    else:
        # Fallback to simple success response
        status_match = re.search(r'status=(\d+)', response_text)
        http_status = status_match.group(1) if status_match else "200"
        
        return [
            f'            return self._create_success_response(',
            f'                http_status={http_status}',
            f'            )'
        ]

if __name__ == "__main__":
    comprehensive_replacement()

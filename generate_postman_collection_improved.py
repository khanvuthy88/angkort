#!/usr/bin/env python3
"""
Improved Odoo API to Postman Collection Generator

This script extracts API endpoints from Odoo controller files and generates
a Postman collection JSON file that can be imported into Postman.

Usage:
    python generate_postman_collection_improved.py
"""

import os
import re
import json
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class ImprovedOdooAPIExtractor:
    """Extract API endpoints from Odoo controller files with improved parsing."""
    
    def __init__(self, controllers_dir: str = "e_menu/controllers"):
        self.controllers_dir = Path(controllers_dir)
        self.base_url = "/angkort/api/v1"
        self.endpoints = []
        
    def extract_endpoints_from_file(self, file_path: Path) -> List[Dict]:
        """Extract endpoints from a single controller file."""
        endpoints = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return endpoints
            
        # Find all @http.route decorators with better pattern matching
        route_pattern = r'@http\.route\(([^)]+)\)\s*\n\s*def\s+(\w+)\s*\([^)]*\):\s*\n\s*"""(.*?)"""'
        matches = re.findall(route_pattern, content, re.DOTALL | re.MULTILINE)
        
        for route_args, func_name, docstring in matches:
            endpoint = self._parse_route_decorator(route_args, func_name, docstring, file_path.name)
            if endpoint:
                endpoints.append(endpoint)
                
        return endpoints
    
    def _parse_route_decorator(self, route_args: str, func_name: str, docstring: str, filename: str) -> Optional[Dict]:
        """Parse route decorator arguments and extract endpoint information."""
        try:
            # Extract URL pattern - handle f-strings better
            url = self._extract_url_from_route_args(route_args)
            if not url:
                return None
                
            # Extract HTTP method
            method = self._extract_method_from_route_args(route_args)
            
            # Extract authentication
            auth = self._extract_auth_from_route_args(route_args)
            
            # Extract CORS
            cors = 'cors="*"' in route_args
            
            # Parse docstring
            parsed_doc = self._parse_docstring(docstring)
            
            endpoint = {
                "name": f"{func_name} - {parsed_doc.get('summary', func_name)}",
                "url": url,
                "method": method,
                "auth": auth,
                "cors": cors,
                "description": parsed_doc.get('description', ''),
                "request_body": parsed_doc.get('request_body', {}),
                "response_example": parsed_doc.get('response_example', {}),
                "query_params": parsed_doc.get('query_params', []),
                "path_params": parsed_doc.get('path_params', []),
                "status_codes": parsed_doc.get('status_codes', []),
                "filename": filename,
                "function_name": func_name
            }
            
            return endpoint
            
        except Exception as e:
            print(f"Error parsing route decorator: {e}")
            return None
    
    def _extract_url_from_route_args(self, route_args: str) -> Optional[str]:
        """Extract URL from route arguments, handling f-strings."""
        # Try to find f-string URL first
        f_string_pattern = r'f?"([^"]*\{[^}]*\}[^"]*)"'
        f_match = re.search(f_string_pattern, route_args)
        if f_match:
            url = f_match.group(1)
            # Replace BASE_URL variable
            url = url.replace('{BASE_URL}', self.base_url)
            return url
        
        # Try regular string URL
        string_pattern = r'"([^"]+)"'
        string_match = re.search(string_pattern, route_args)
        if string_match:
            url = string_match.group(1)
            # Replace BASE_URL variable
            url = url.replace('{BASE_URL}', self.base_url)
            return url
        
        return None
    
    def _extract_method_from_route_args(self, route_args: str) -> str:
        """Extract HTTP method from route arguments."""
        method = "GET"  # default
        
        # Check for methods parameter
        if "methods=" in route_args:
            methods_match = re.search(r'methods=\[([^\]]+)\]', route_args)
            if methods_match:
                methods_str = methods_match.group(1)
                if '"POST"' in methods_str:
                    method = "POST"
                elif '"PUT"' in methods_str:
                    method = "PUT"
                elif '"DELETE"' in methods_str:
                    method = "DELETE"
        
        # Check for type parameter
        if 'type="http"' in route_args:
            # Look for methods in the same line or nearby
            if '"POST"' in route_args:
                method = "POST"
            elif '"PUT"' in route_args:
                method = "PUT"
            elif '"DELETE"' in route_args:
                method = "DELETE"
        
        return method
    
    def _extract_auth_from_route_args(self, route_args: str) -> str:
        """Extract authentication from route arguments."""
        auth = "public"  # default
        auth_match = re.search(r'auth="([^"]+)"', route_args)
        if auth_match:
            auth = auth_match.group(1)
        return auth
    
    def _parse_docstring(self, docstring: str) -> Dict:
        """Parse docstring to extract structured information."""
        parsed = {
            'summary': '',
            'description': '',
            'request_body': {},
            'response_example': {},
            'query_params': [],
            'path_params': [],
            'status_codes': []
        }
        
        lines = docstring.strip().split('\n')
        current_section = None
        description_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect sections
            if line.startswith('Endpoint:'):
                current_section = 'endpoint'
                continue
            elif line.startswith('Request:') or line.startswith('Request Body:'):
                current_section = 'request'
                continue
            elif line.startswith('Returns:') or line.startswith('Response:'):
                current_section = 'response'
                continue
            elif line.startswith('Parameters:') or line.startswith('Query Parameters:'):
                current_section = 'parameters'
                continue
            elif line.startswith('Status Codes:'):
                current_section = 'status_codes'
                continue
            elif line.startswith('Example') and 'Request' in line:
                current_section = 'example_request'
                continue
            elif line.startswith('Example') and 'Response' in line:
                current_section = 'example_response'
                continue
            elif line.startswith('Auth:') or line.startswith('Content-Type:'):
                continue
                
            # Extract information based on current section
            if current_section == 'endpoint':
                if not parsed['summary']:
                    parsed['summary'] = line
            elif current_section == 'request':
                if '{' in line and '}' in line:
                    try:
                        # Try to parse JSON-like structure
                        json_str = self._extract_json_from_line(line)
                        if json_str:
                            parsed['request_body'] = json.loads(json_str)
                    except:
                        description_lines.append(line)
                else:
                    description_lines.append(line)
            elif current_section == 'response':
                if '{' in line and '}' in line:
                    try:
                        json_str = self._extract_json_from_line(line)
                        if json_str:
                            parsed['response_example'] = json.loads(json_str)
                    except:
                        description_lines.append(line)
                else:
                    description_lines.append(line)
            elif current_section == 'parameters':
                if ':' in line:
                    param_name, param_desc = line.split(':', 1)
                    parsed['query_params'].append({
                        'name': param_name.strip(),
                        'description': param_desc.strip()
                    })
            elif current_section == 'status_codes':
                if ':' in line:
                    code, desc = line.split(':', 1)
                    parsed['status_codes'].append({
                        'code': code.strip(),
                        'description': desc.strip()
                    })
            elif current_section == 'example_request':
                if '{' in line and '}' in line:
                    try:
                        json_str = self._extract_json_from_line(line)
                        if json_str:
                            parsed['request_body'] = json.loads(json_str)
                    except:
                        pass
            elif current_section == 'example_response':
                if '{' in line and '}' in line:
                    try:
                        json_str = self._extract_json_from_line(line)
                        if json_str:
                            parsed['response_example'] = json.loads(json_str)
                    except:
                        pass
            else:
                if not parsed['summary']:
                    parsed['summary'] = line
                else:
                    description_lines.append(line)
        
        parsed['description'] = '\n'.join(description_lines)
        return parsed
    
    def _extract_json_from_line(self, line: str) -> Optional[str]:
        """Extract JSON string from a line of text."""
        # Find the first { and last }
        start = line.find('{')
        end = line.rfind('}')
        if start != -1 and end != -1 and end > start:
            return line[start:end+1]
        return None
    
    def extract_all_endpoints(self) -> List[Dict]:
        """Extract endpoints from all controller files."""
        if not self.controllers_dir.exists():
            print(f"Controllers directory not found: {self.controllers_dir}")
            return []
        
        all_endpoints = []
        
        for file_path in self.controllers_dir.glob("*.py"):
            if file_path.name in ["__init__.py", "definitions.ts"]:
                continue
                
            print(f"Processing {file_path.name}...")
            endpoints = self.extract_endpoints_from_file(file_path)
            all_endpoints.extend(endpoints)
            print(f"Found {len(endpoints)} endpoints in {file_path.name}")
        
        return all_endpoints


class ImprovedPostmanCollectionGenerator:
    """Generate Postman collection from extracted endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8069"):
        self.base_url = base_url.rstrip('/')
        
    def generate_collection(self, endpoints: List[Dict], collection_name: str = "Angkort API") -> Dict:
        """Generate Postman collection JSON structure."""
        
        # Group endpoints by controller
        grouped_endpoints = {}
        for endpoint in endpoints:
            controller_name = endpoint['filename'].replace('.py', '').replace('_', ' ').title()
            if controller_name not in grouped_endpoints:
                grouped_endpoints[controller_name] = []
            grouped_endpoints[controller_name].append(endpoint)
        
        # Create collection structure
        collection = {
            "info": {
                "name": collection_name,
                "description": f"API collection for Angkort Odoo application\nGenerated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [],
            "variable": [
                {
                    "key": "base_url",
                    "value": self.base_url,
                    "type": "string"
                },
                {
                    "key": "access_token",
                    "value": "your_access_token_here",
                    "type": "string"
                }
            ]
        }
        
        # Add folders for each controller
        for controller_name, controller_endpoints in grouped_endpoints.items():
            folder = {
                "name": controller_name,
                "item": []
            }
            
            for endpoint in controller_endpoints:
                request_item = self._create_request_item(endpoint)
                folder["item"].append(request_item)
            
            collection["item"].append(folder)
        
        return collection
    
    def _create_request_item(self, endpoint: Dict) -> Dict:
        """Create a Postman request item from endpoint data."""
        
        # Build URL with variables
        url = endpoint['url']
        if url.startswith('/'):
            url = f"{{{{base_url}}}}{url}"
        
        # Extract path parameters
        path_variables = []
        path_params = re.findall(r'<([^>]+)>', url)
        for param in path_params:
            if ':' in param:
                param_type, param_name = param.split(':', 1)
                path_variables.append({
                    "key": param_name,
                    "value": f"{{{{{param_name}}}}}",
                    "description": f"{param_name} parameter"
                })
        
        # Create request structure
        request_item = {
            "name": endpoint['name'],
            "request": {
                "method": endpoint['method'],
                "header": [],
                "url": {
                    "raw": url,
                    "host": ["{{base_url}}"],
                    "path": url.replace("{{base_url}}", "").strip('/').split('/'),
                    "variable": path_variables
                },
                "description": endpoint['description']
            },
            "response": []
        }
        
        # Add authentication headers if needed
        if endpoint['auth'] != 'public':
            request_item["request"]["header"].append({
                "key": "Authorization",
                "value": "Bearer {{access_token}}",
                "type": "text"
            })
        
        # Add CORS headers if needed
        if endpoint['cors']:
            request_item["request"]["header"].append({
                "key": "Access-Control-Allow-Origin",
                "value": "*",
                "type": "text"
            })
        
        # Add Content-Type for POST requests
        if endpoint['method'] == 'POST':
            request_item["request"]["header"].append({
                "key": "Content-Type",
                "value": "application/json",
                "type": "text"
            })
        
        # Add request body for POST requests
        if endpoint['method'] == 'POST' and endpoint['request_body']:
            request_item["request"]["body"] = {
                "mode": "raw",
                "raw": json.dumps(endpoint['request_body'], indent=2),
                "options": {
                    "raw": {
                        "language": "json"
                    }
                }
            }
        
        # Add query parameters
        if endpoint['query_params']:
            request_item["request"]["url"]["query"] = []
            for param in endpoint['query_params']:
                request_item["request"]["url"]["query"].append({
                    "key": param['name'],
                    "value": f"{{{{{param['name']}}}}}",
                    "description": param['description']
                })
        
        # Add example response
        if endpoint['response_example']:
            request_item["response"].append({
                "name": "Example Response",
                "originalRequest": request_item["request"],
                "status": "OK",
                "code": 200,
                "_postman_previewlanguage": "json",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "cookie": [],
                "body": json.dumps(endpoint['response_example'], indent=2)
            })
        
        return request_item


def main():
    """Main function to generate Postman collection."""
    print("🚀 Starting Improved Odoo API to Postman Collection Generator...")
    
    # Extract endpoints
    extractor = ImprovedOdooAPIExtractor()
    endpoints = extractor.extract_all_endpoints()
    
    if not endpoints:
        print("❌ No endpoints found!")
        return
    
    print(f"✅ Found {len(endpoints)} endpoints")
    
    # Generate Postman collection
    generator = ImprovedPostmanCollectionGenerator()
    collection = generator.generate_collection(endpoints)
    
    # Save to file
    output_file = "Angkort_API_Collection_Improved.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Postman collection saved to: {output_file}")
    print(f"📊 Collection contains {len(collection['item'])} folders and {len(endpoints)} requests")
    
    # Print summary
    print("\n📋 Endpoints Summary:")
    for endpoint in endpoints:
        print(f"  {endpoint['method']} {endpoint['url']} - {endpoint['name']}")
    
    print(f"\n🎉 Import '{output_file}' into Postman to get started!")
    print("\n📝 Setup Instructions:")
    print("1. Open Postman")
    print("2. Click 'Import'")
    print("3. Select the generated JSON file")
    print("4. Set the 'base_url' variable to your Odoo server URL")
    print("5. Set the 'access_token' variable if using authenticated endpoints")


if __name__ == "__main__":
    main() 
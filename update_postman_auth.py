#!/usr/bin/env python3
"""
Script to update Postman collection with proper Bearer Token authorization
based on route authentication requirements.
"""

import json
import re

# Routes that require authentication (auth="angkit") - with method specificity
AUTHENTICATED_ROUTES = [
    # Order routes
    ("/angkort/api/v1/my/order", ["GET", "POST"]),
    ("/angkort/api/v1/my/order/.*", ["GET"]),
    ("/angkort/api/v1/cart/checkout", ["POST"]),
    ("/angkort/api/v1/order", ["POST"]),
    
    # Shop management routes (create, update, delete)
    ("/angkort/api/v1/shop", ["POST", "PUT", "DELETE"]),
    ("/angkort/api/v1/shop/create", ["POST"]),
    
    # Product management routes (create, update, delete)
    ("/angkort/api/v1/shop/.*/product", ["POST", "PUT", "DELETE"]),
    ("/angkort/api/v1/shop/.*/product/.*/calculate-price", ["POST"]),
    
    # Category management routes (create, update, delete)
    ("/angkort/api/v1/shop/.*/product/category", ["POST", "PUT", "DELETE"]),
    
    # Image upload
    ("/angkort/api/v1/image/add", ["POST"]),
    
    # Variant management routes
    ("/angkort/api/v1/shop/.*/product/.*/value", ["GET", "POST", "PUT", "DELETE"]),
    ("/angkort/api/v1/shop/.*/product/variant/value", ["POST", "PUT", "DELETE"]),
    ("/angkort/api/v1/shop/.*/product/variant", ["GET", "POST", "PUT", "DELETE"]),
    
    # Logout
    ("/angkort/api/v1/logout", ["POST"])
]

# Routes that are public (auth="public") - with method specificity
PUBLIC_ROUTES = [
    # Authentication
    ("/angkort/api/v1/login", ["POST"]),
    
    # Public read routes
    ("/angkort/api/v1/shop", ["GET"]),
    ("/angkort/api/v1/shop/.*/product", ["GET"]),
    ("/angkort/api/v1/shop/.*/product/category", ["GET"]),
    ("/angkort/api/v1/industries", ["GET"]),
    ("/angkort/api/v1/product/category", ["GET"]),
    ("/angkort/api/v1/product/.*", ["GET"]),
    ("/angkort/api/v1/product/variant", ["GET"]),
    ("/angkort/api/v1/sale", ["GET"])
]

def route_matches_pattern(route, method, patterns):
    """Check if a route matches any of the given patterns with method."""
    for pattern, allowed_methods in patterns:
        if re.match(pattern, route) and method in allowed_methods:
            return True
    return False

def requires_auth(url_path, method):
    """Determine if a route requires authentication based on URL and method."""
    # Login route is always public
    if url_path == "/angkort/api/v1/login" and method == "POST":
        return False
    
    # Logout route always requires auth
    if url_path == "/angkort/api/v1/logout" and method == "POST":
        return True
    
    # Check if it matches authenticated patterns
    if route_matches_pattern(url_path, method, AUTHENTICATED_ROUTES):
        return True
    
    # Check if it matches public patterns
    if route_matches_pattern(url_path, method, PUBLIC_ROUTES):
        return False
    
    # Default to requiring auth for safety
    return True

def update_request_auth(request, requires_authentication):
    """Update request authentication based on requirements."""
    if requires_authentication:
        # Add Bearer Token auth
        request["auth"] = {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{api_key}}",
                    "type": "string"
                }
            ]
        }
    else:
        # Remove auth if present
        if "auth" in request:
            del request["auth"]

def update_collection_auth(collection_data):
    """Update the entire collection with proper authentication."""
    # Remove collection-level auth since we'll set it per request
    if "auth" in collection_data:
        del collection_data["auth"]
    
    def update_item_auth(item):
        """Recursively update items in the collection."""
        if "item" in item:
            # This is a folder, update its children
            for sub_item in item["item"]:
                update_item_auth(sub_item)
        elif "request" in item:
            # This is a request, update its auth
            request = item["request"]
            url = request.get("url", {})
            
            # Extract the path
            if "raw" in url:
                # Parse the raw URL to get the path
                raw_url = url["raw"]
                # Extract path from raw URL (remove host and query params)
                if "{{baseUrl}}" in raw_url:
                    path_part = raw_url.split("{{baseUrl}}")[1]
                    # Remove query parameters
                    path = path_part.split("?")[0]
                else:
                    # Fallback to path array
                    path = "/" + "/".join(url.get("path", []))
            else:
                # Use path array
                path = "/" + "/".join(url.get("path", []))
            
            method = request.get("method", "GET")
            needs_auth = requires_auth(path, method)
            
            update_request_auth(request, needs_auth)
            
            # Update description to indicate auth requirement
            if "description" in item:
                if needs_auth:
                    if "Requires authentication" not in item["description"]:
                        item["description"] += " (Requires Bearer Token authentication)"
                else:
                    if "Public endpoint" not in item["description"]:
                        item["description"] += " (Public endpoint - no authentication required)"
    
    # Update all items
    for item in collection_data.get("item", []):
        update_item_auth(item)

def main():
    """Main function to update the Postman collection."""
    # Read the current collection
    with open("Angkort_API_Collection_Refactored.json", "r", encoding="utf-8") as f:
        collection = json.load(f)
    
    # Update the collection
    update_collection_auth(collection)
    
    # Write the updated collection
    with open("Angkort_API_Collection_Refactored.json", "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    
    print("✅ Postman collection updated with proper Bearer Token authorization!")
    print("📋 Routes with auth='angkit' now have Bearer Token authorization")
    print("🌐 Public routes (auth='public') have no authorization requirement")
    print("🔐 Collection-level auth removed in favor of per-request auth")

if __name__ == "__main__":
    main() 
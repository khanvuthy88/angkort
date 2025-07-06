#!/bin/bash

# Angkort API Postman Collection Generator Script
# This script regenerates the Postman collection from your Odoo controllers

echo "🔄 Regenerating Angkort API Postman Collection..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if the improved generator script exists
if [ ! -f "generate_postman_collection_improved.py" ]; then
    echo "❌ generate_postman_collection_improved.py not found"
    exit 1
fi

# Run the generator
echo "📝 Running collection generator..."
python3 generate_postman_collection_improved.py

# Check if generation was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Collection generated successfully!"
    echo "📁 Files created:"
    echo "   - Angkort_API_Collection_Improved.json (recommended)"
    echo "   - Angkort_API_Collection.json (basic version)"
    echo ""
    echo "📋 Next steps:"
    echo "1. Open Postman"
    echo "2. Import 'Angkort_API_Collection_Improved.json'"
    echo "3. Set environment variables (base_url, access_token)"
    echo "4. Start testing your API endpoints!"
else
    echo "❌ Failed to generate collection"
    exit 1
fi 
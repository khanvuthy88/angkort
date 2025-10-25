# Installation Guide - Candidate Auto-Extraction Feature

## Quick Start

### Step 1: Install Python Packages

Navigate to the module directory:
```bash
cd /Users/khanvuthy/Documents/odoo/odoo18-project/angkort/angkot_recruitement
```

Install all Python dependencies:
```bash
pip install -r requirements.txt
```

### Step 2: Install System Dependencies (for OCR support)

Choose your operating system:

#### macOS (your current OS):
```bash
# Install Tesseract OCR
brew install tesseract

# Install Poppler (for PDF to image conversion)
brew install poppler

# Verify installation
tesseract --version
pdfinfo -v
```

#### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils

# Verify installation
tesseract --version
pdfinfo -v
```

#### Windows:
1. **Tesseract OCR:**
   - Download from: https://github.com/UB-Mannheim/tesseract/wiki
   - Install and add to PATH
   
2. **Poppler:**
   - Download from: https://github.com/oschwartz10612/poppler-windows/releases/
   - Extract and add bin folder to PATH

### Step 3: Verify Installation

Test if all packages are available:
```bash
python3 << EOF
import sys

packages = {
    'PyPDF2': 'PyPDF2',
    'pdfplumber': 'pdfplumber',
    'pdf2image': 'pdf2image',
    'pytesseract': 'pytesseract',
    'docx2txt': 'docx2txt',
    'phonenumbers': 'phonenumbers',
    'PIL': 'Pillow'
}

print("Checking Python packages...")
for pkg, pip_name in packages.items():
    try:
        __import__(pkg)
        print(f"✓ {pip_name} installed")
    except ImportError:
        print(f"✗ {pip_name} NOT installed - run: pip install {pip_name}")

print("\nChecking system dependencies...")
import subprocess

# Check Tesseract
try:
    result = subprocess.run(['tesseract', '--version'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Tesseract OCR installed")
    else:
        print("✗ Tesseract OCR NOT installed")
except FileNotFoundError:
    print("✗ Tesseract OCR NOT installed")

# Check Poppler
try:
    result = subprocess.run(['pdfinfo', '-v'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Poppler utilities installed")
    else:
        print("✗ Poppler utilities NOT installed")
except FileNotFoundError:
    print("✗ Poppler utilities NOT installed")

print("\nInstallation check complete!")
EOF
```

### Step 4: Update Odoo Module

Restart your Odoo server and upgrade the module:

```bash
# Stop Odoo if running
# Then restart with upgrade flag
./odoo-bin -u angkot_recruitement -d your_database_name

# Or if using systemd:
sudo systemctl restart odoo
# Then upgrade via Odoo UI: Apps > angkot_recruitement > Upgrade
```

## Package Details

### Required Packages (Core Functionality)

| Package | Purpose | Installation |
|---------|---------|--------------|
| PyPDF2 | Basic PDF text extraction | `pip install PyPDF2` |
| pdfplumber | Enhanced PDF extraction | `pip install pdfplumber` |
| python-docx2txt | Word document processing | `pip install python-docx2txt` |
| phonenumbers | Phone number parsing | `pip install phonenumbers` |

### Optional Packages (OCR Support for Scanned Documents)

| Package | Purpose | Installation |
|---------|---------|--------------|
| pdf2image | Convert PDF to images | `pip install pdf2image` |
| pytesseract | OCR text recognition | `pip install pytesseract` |
| Pillow | Image processing | `pip install Pillow` |
| Tesseract | OCR engine (system) | See Step 2 |
| Poppler | PDF utilities (system) | See Step 2 |

## Recommended Installation (All Features)

For the best experience with both text-based and scanned documents:

```bash
# Install all Python packages
pip install PyPDF2>=3.0.0 \
            pdfplumber>=0.10.0 \
            pdf2image>=1.16.0 \
            pytesseract>=0.3.10 \
            Pillow>=10.0.0 \
            python-docx2txt>=0.8 \
            phonenumbers>=8.13.0

# Install system dependencies (macOS)
brew install tesseract poppler

# Or (Ubuntu/Debian)
sudo apt-get install tesseract-ocr poppler-utils
```

## Minimal Installation (Text Documents Only)

If you only need to process text-based documents (no OCR):

```bash
pip install PyPDF2 pdfplumber python-docx2txt phonenumbers
```

This will work for:
- ✓ Text-based PDFs
- ✓ Word documents (.docx, .doc)
- ✓ Plain text files (.txt)
- ✗ Scanned PDFs (will skip OCR)
- ✗ Image-based documents

## Additional Package Recommendations

### pdfplumber vs PyPDF2

**pdfplumber** (Recommended):
- Better text extraction quality
- Handles tables and structured content
- More accurate layout preservation
- Better for modern PDFs

**PyPDF2** (Fallback):
- Lighter weight
- Works with older PDFs
- Used as backup when pdfplumber fails

### phonenumbers Library

This library provides:
- International phone number parsing
- Format validation
- Country/region detection
- Multiple format output (E164, INTERNATIONAL, etc.)

Example capabilities:
```python
# Can parse and validate:
"+855 12 345 678"  → +855 12 345 678
"(123) 456-7890"   → +1 123-456-7890
"012-345-678"      → +855 12 345 678 (if region is KH)
```

## Troubleshooting Installation

### Issue: "ModuleNotFoundError: No module named 'xxx'"

**Solution:**
```bash
# Make sure you're using the same Python as Odoo
which python3
# or
which python

# Install with the correct pip
pip3 install -r requirements.txt
# or use the full path to Odoo's Python
/path/to/odoo/venv/bin/pip install -r requirements.txt
```

### Issue: "TesseractNotFoundError"

**Solution:**
```bash
# macOS
brew install tesseract
export PATH="/usr/local/bin:$PATH"

# Ubuntu
sudo apt-get install tesseract-ocr

# Windows - add Tesseract to PATH after installation
# Default location: C:\Program Files\Tesseract-OCR
```

### Issue: "Unable to get page count. Is poppler installed?"

**Solution:**
```bash
# macOS
brew install poppler

# Ubuntu
sudo apt-get install poppler-utils

# Windows
# Download and extract poppler
# Add C:\path\to\poppler\bin to PATH
```

### Issue: Odoo Module Won't Upgrade

**Solution:**
```bash
# Check Odoo logs for specific errors
tail -f /var/log/odoo/odoo-server.log

# Common issues:
# 1. Python package not found - reinstall packages
# 2. XML syntax error - check views/hr_candidate_views.xml
# 3. Import error - check models/__init__.py includes hr_candidate
```

## Testing the Installation

### Quick Test

1. Log into Odoo
2. Go to Recruitment > Candidates
3. Create a new candidate
4. Upload a CV/Resume PDF
5. Check if email and phone are automatically filled
6. Check the "Extraction Log" tab for details

### Test with Sample Document

Create a test PDF with this content:
```
John Doe
Email: john.doe@example.com
Phone: +855 12 345 678
Mobile: 012-345-678
```

Upload it to a candidate and verify extraction works.

## Performance Notes

- **Text PDFs**: Process in < 1 second
- **Scanned PDFs (OCR)**: 5-15 seconds per page
- **DOCX files**: < 1 second
- **OCR processes only first 3 pages** to avoid long processing times

## Updating Dependencies

To update all packages to latest versions:
```bash
pip install --upgrade PyPDF2 pdfplumber pdf2image pytesseract python-docx2txt phonenumbers Pillow
```

## Production Considerations

For production environments:
1. Install system dependencies globally
2. Use a virtual environment for Python packages
3. Consider using a task queue for OCR operations if processing many documents
4. Monitor log file size of extraction logs
5. Consider memory limits for OCR operations

## Getting Help

If you encounter issues:
1. Check the extraction log on the candidate form
2. Review Odoo server logs: `/var/log/odoo/odoo-server.log`
3. Run the verification script above to check all dependencies
4. Test with a simple text-based PDF first
5. Gradually add OCR functionality once basic extraction works

## Next Steps

After installation:
1. Read `CANDIDATE_EXTRACTION_FEATURE.md` for usage details
2. Test with various document types
3. Configure per-candidate extraction preferences
4. Monitor extraction logs for accuracy
5. Provide feedback for improvements


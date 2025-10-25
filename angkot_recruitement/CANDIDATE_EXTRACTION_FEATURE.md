# Candidate Contact Information Auto-Extraction Feature

## Overview

This feature automatically extracts email addresses and phone numbers from candidate attachments (CV/Resume files) and populates the candidate record automatically.

## Supported File Formats

- **PDF** (text-based and scanned/OCR)
- **DOCX/DOC** (Microsoft Word documents)
- **TXT** (Plain text files)

## Features

### Automatic Extraction
- Automatically extracts contact information when attachments are uploaded
- Works during candidate creation and when attachments are added later
- Only fills empty fields - won't overwrite existing data
- Logs all extraction attempts for debugging

### Manual Extraction
- "Extract Contact Info" button on candidate form
- Allows manual trigger of extraction process
- Useful for reprocessing or when automatic extraction is disabled

### Multiple Extraction Methods
1. **pdfplumber** - Primary method for text-based PDFs (best results)
2. **PyPDF2** - Fallback method for PDFs
3. **OCR (Tesseract)** - For scanned documents and images in PDFs
4. **docx2txt** - For Microsoft Word documents

### Intelligent Contact Detection
- **Email Detection**: Advanced regex patterns to find valid email addresses
- **Phone Detection**: 
  - Uses `phonenumbers` library for accurate parsing
  - Supports international phone formats
  - Validates against country/region (defaults to Cambodia - KH)
  - Falls back to regex patterns if library unavailable

## Installation

### 1. Install Python Dependencies

```bash
cd /path/to/angkort/angkot_recruitement
pip install -r requirements.txt
```

Or install individually:
```bash
pip install PyPDF2 pdfplumber pdf2image pytesseract python-docx2txt phonenumbers Pillow
```

### 2. Install System Dependencies

#### For OCR (Optional but recommended for scanned documents):

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

#### For PDF to Image Conversion (Required for OCR):

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

**Windows:**
Download from: https://github.com/oschwartz10612/poppler-windows/releases/

### 3. Update/Restart Odoo Module

```bash
# Restart Odoo server
# Then upgrade the module
odoo-bin -u angkot_recruitement -d your_database
```

## Usage

### Automatic Mode (Default)

1. Create a new candidate or open an existing one
2. Ensure "Auto-Extract Contact Info" toggle is enabled (default: ON)
3. Upload a CV/Resume attachment
4. Email and phone will be automatically extracted and filled

### Manual Mode

1. Open a candidate record
2. Click the "Extract Contact Info" button in the header
3. System will process all attachments and extract information
4. View the "Extraction Log" tab for details

### Configuration Options

- **Auto-Extract Enabled**: Toggle to enable/disable automatic extraction per candidate
- **Extraction Log**: View detailed logs of all extraction attempts
- **Last Extraction Date**: Timestamp of the most recent extraction

## How It Works

### Extraction Process Flow

```
1. Attachment uploaded/added to candidate
   ↓
2. Check if auto-extraction is enabled
   ↓
3. Identify file type (PDF/DOCX/TXT)
   ↓
4. Extract text using appropriate method:
   - PDF: pdfplumber → PyPDF2 → OCR
   - DOCX: docx2txt
   - TXT: Direct text read
   ↓
5. Search for email patterns in extracted text
   ↓
6. Search for phone patterns in extracted text
   ↓
7. Update candidate if fields are empty
   ↓
8. Post message to chatter with results
   ↓
9. Log extraction details
```

### Email Detection Pattern

Matches standard email format:
- `name@domain.com`
- `first.last@company.co.uk`
- `user+tag@example.org`

### Phone Detection Patterns

Supports various formats:
- International: `+855 12 345 678`
- Standard: `(123) 456-7890`
- Simple: `123-456-7890`
- Cambodia: `+855-12-345-678`

## Field Mapping

| Extracted Data | Candidate Field | Notes |
|----------------|-----------------|-------|
| First email found | `email_from` | Only if empty |
| First phone found | `partner_phone` | Only if empty |
| Additional emails | Chatter message | Logged for reference |
| Additional phones | Chatter message | Logged for reference |

## Extraction Log

The extraction log records:
- Timestamp of each extraction attempt
- Files processed
- Number of emails/phones found
- Success/error messages
- Which fields were updated

Example log:
```
[2025-10-11 14:30:00]
Processed resume.pdf: Found 2 emails, 1 phones
Set email to: john.doe@example.com
Set phone to: +855 12 345 678
Other emails found: backup@example.com
==================================================
```

## Troubleshooting

### No Text Extracted from PDF

**Cause**: PDF is scanned/image-based and OCR is not installed

**Solution**: Install Tesseract and poppler-utils (see Installation section)

### Phone Numbers Not Detected

**Cause**: Missing `phonenumbers` library or unusual phone format

**Solution**: 
1. Install phonenumbers: `pip install phonenumbers`
2. Check extraction log for found patterns
3. Phone must have at least 7 digits to be considered valid

### Email Not Extracted

**Cause**: Email format is non-standard or embedded in image

**Solution**:
1. Ensure OCR is working for image-based documents
2. Check extraction log to see if email was found but not the first one
3. Manually add from chatter message showing "Other emails found"

### Module Won't Load

**Cause**: Missing Python dependencies

**Solution**:
```bash
# Check Odoo logs for missing modules
# Install missing dependencies:
pip install PyPDF2 pdfplumber python-docx2txt phonenumbers
```

### OCR is Slow

**Cause**: Processing high-resolution images

**Solution**: OCR is only used as a fallback. For best performance:
1. Use text-based PDFs when possible
2. OCR only processes first 3 pages by default
3. Adjust DPI in code if needed (default: 300)

## Performance Considerations

- Text-based PDFs: Very fast (<1 second)
- Scanned PDFs with OCR: 5-15 seconds per page
- DOCX files: Very fast (<1 second)
- The extraction runs asynchronously and won't block the UI

## Security & Privacy

- All processing is done server-side
- No data is sent to external services
- Extraction uses only installed libraries
- Only candidate manager and HR users can trigger extraction

## API Integration

For programmatic extraction:

```python
# Python example
candidate = env['hr.candidate'].browse(candidate_id)

# Enable auto-extraction
candidate.write({'auto_extract_enabled': True})

# Manual extraction
candidate._auto_extract_from_attachments()

# Check results
print(f"Email: {candidate.email_from}")
print(f"Phone: {candidate.partner_phone}")
print(f"Log: {candidate.extraction_log}")
```

## Future Enhancements

Potential improvements:
- Extract additional fields (name, address, skills)
- Support more file formats (RTF, HTML)
- Multiple language OCR support
- AI-powered structured data extraction
- Duplicate detection before extraction

## Support

For issues or questions:
1. Check the Extraction Log tab on candidate form
2. Review Odoo server logs for detailed error messages
3. Verify all dependencies are installed correctly
4. Test with different file formats to isolate issues

## Credits

This feature uses the following open-source libraries:
- PyPDF2 - PDF processing
- pdfplumber - Enhanced PDF text extraction
- Tesseract OCR - Optical character recognition
- phonenumbers - Phone number parsing
- python-docx2txt - Word document processing


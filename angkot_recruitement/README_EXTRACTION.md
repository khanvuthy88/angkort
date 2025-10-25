# 🚀 Candidate Contact Auto-Extraction Feature

Automatically extract email addresses and phone numbers from candidate CV/Resume files (PDF, DOCX, TXT) and populate candidate records.

## 📋 Quick Overview

This feature extends the `hr.candidate` model to automatically:
- ✅ Extract email addresses from uploaded documents
- ✅ Extract phone numbers with international format support
- ✅ Handle both text-based and scanned (OCR) documents
- ✅ Support PDF, DOCX, DOC, and TXT files
- ✅ Log all extraction attempts for debugging
- ✅ Prevent overwriting existing contact information

## 🎯 Key Features

### Automatic & Manual Modes
- **Automatic**: Extracts on file upload (default enabled)
- **Manual**: Click button to trigger extraction anytime

### Multiple File Format Support
- 📄 **PDF**: Text-based and scanned/image PDFs
- 📝 **DOCX/DOC**: Microsoft Word documents  
- 📃 **TXT**: Plain text files

### Intelligent Extraction
- **Email**: Advanced regex patterns for various email formats
- **Phone**: Uses `phonenumbers` library for accurate international parsing
- **Multi-method**: Falls back through multiple extraction techniques
- **Smart Fill**: Only fills empty fields, won't overwrite existing data

### Logging & Transparency
- View extraction logs directly in candidate form
- Chatter messages with extraction results
- Timestamp tracking for audit purposes

## 📦 Installation

### 1️⃣ Quick Install (Recommended)

```bash
# Navigate to module directory
cd /Users/khanvuthy/Documents/odoo/odoo18-project/angkort/angkot_recruitement

# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies (macOS)
brew install tesseract poppler

# Restart Odoo and upgrade module
# Then in Odoo: Apps > angkot_recruitement > Upgrade
```

### 2️⃣ Verify Installation

```bash
# Run test script to check all dependencies
python3 test_extraction.py
```

Expected output:
```
✓ Core functionality ready!
✓ OCR functionality ready!
✅ You can now use the extraction feature!
```

### 3️⃣ Individual Package Installation

If you prefer to install packages individually:

```bash
# Required for all features
pip install PyPDF2 pdfplumber python-docx2txt phonenumbers

# Required for OCR (scanned documents)
pip install pdf2image pytesseract Pillow

# System dependencies (macOS)
brew install tesseract poppler

# Or Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils
```

## 🎮 Usage

### Automatic Mode (Default)

1. Open/Create a candidate in Odoo
2. Ensure **"Auto-Extract Contact Info"** toggle is ON (default)
3. Upload a CV/Resume file
4. Email and phone are automatically extracted! ✨

### Manual Mode

1. Open a candidate record with attachments
2. Click **"Extract Contact Info"** button in header
3. View results in Chatter and **"Extraction Log"** tab

### Configuration

On each candidate form:
- **Auto-Extract Contact Info**: Toggle to enable/disable per candidate
- **Last Extraction Date**: When extraction last ran
- **Extraction Log**: Detailed log of all extraction attempts

## 📊 What Gets Extracted

| Data Found | Field Updated | Behavior |
|------------|---------------|----------|
| First email | `email_from` | Only if empty |
| First phone | `partner_phone` | Only if empty |
| Additional emails | Chatter message | For reference |
| Additional phones | Chatter message | For reference |

## 🔍 How It Works

### Extraction Flow

```
1. File uploaded to candidate
   ↓
2. Auto-extract enabled? → Yes
   ↓
3. Identify file type (PDF/DOCX/TXT)
   ↓
4. Extract text:
   • PDF: pdfplumber → PyPDF2 → OCR
   • DOCX: docx2txt
   • TXT: direct read
   ↓
5. Find emails using regex patterns
   ↓
6. Find phones using phonenumbers library
   ↓
7. Update empty fields only
   ↓
8. Post message to chatter
   ↓
9. Log results
```

### Supported Patterns

**Email Examples:**
- `john.doe@example.com`
- `jane.smith+tag@company.co.uk`
- `contact@sub.domain.org`

**Phone Examples:**
- `+855 12 345 678` (Cambodia)
- `(123) 456-7890` (US)
- `012-345-678` (Local)
- `+1-555-123-4567` (International)

## 📚 Documentation Files

| File | Description |
|------|-------------|
| `INSTALLATION_GUIDE.md` | Detailed installation instructions |
| `CANDIDATE_EXTRACTION_FEATURE.md` | Complete feature documentation |
| `requirements.txt` | Python package dependencies |
| `test_extraction.py` | Dependency verification script |
| `README_EXTRACTION.md` | This file - quick reference |

## 🧪 Testing

### Run Dependency Test

```bash
python3 test_extraction.py
```

This will check:
- ✅ All Python packages installed
- ✅ System dependencies available
- ✅ Basic extraction functions work

### Manual Testing

1. Create test candidate
2. Upload sample CV with contact info
3. Check extraction results
4. Review "Extraction Log" tab

### Test Files

Create a simple test resume:
```
JOHN DOE
Software Developer

Email: john.doe@example.com
Phone: +855 12 345 678
Mobile: 012-345-678

[Add more resume content...]
```

Save as PDF and upload to test.

## ⚡ Performance

| Document Type | Speed | Notes |
|---------------|-------|-------|
| Text-based PDF | < 1 sec | Very fast |
| Scanned PDF (OCR) | 5-15 sec/page | Only first 3 pages |
| DOCX | < 1 sec | Very fast |
| TXT | < 1 sec | Instant |

## 🛠️ Troubleshooting

### Common Issues

**"No text extracted"**
- Check if PDF is scanned (needs OCR)
- Verify Tesseract is installed: `tesseract --version`
- Check extraction log for details

**"Module won't load"**
- Missing Python packages: `pip install -r requirements.txt`
- Check Odoo logs: `/var/log/odoo/odoo-server.log`

**"Phone/Email not detected"**
- Check extraction log - might be found but not first
- Verify format is standard
- Try manual extraction button

**"OCR not working"**
- Install Tesseract: `brew install tesseract` (macOS)
- Install Poppler: `brew install poppler` (macOS)
- Run `python3 test_extraction.py` to verify

### Getting Help

1. Check the **Extraction Log** tab on candidate form
2. Review Odoo server logs for errors
3. Run `test_extraction.py` to verify dependencies
4. Read `CANDIDATE_EXTRACTION_FEATURE.md` for details
5. Check `INSTALLATION_GUIDE.md` for setup issues

## 🔐 Security

- All processing is server-side
- No external API calls
- No data leaves your server
- Access controlled by Odoo security rules

## 🎁 Additional Recommendations

### Packages Already Installed

You mentioned having these installed:
- ✅ `pdf2image`
- ✅ `pytesseract`
- ✅ `pillow`
- ✅ `python-docx2txt`
- ✅ `PyPDF2`

### **Highly Recommended** Additional Packages

```bash
# Better PDF extraction (recommended!)
pip install pdfplumber

# Better phone parsing (recommended!)
pip install phonenumbers
```

### Why These Are Better

**pdfplumber** vs PyPDF2:
- ✓ Better text extraction quality
- ✓ Handles complex layouts
- ✓ More accurate for modern PDFs
- ✓ Extracts tables correctly

**phonenumbers**:
- ✓ Validates phone numbers
- ✓ International format support
- ✓ Region-aware parsing
- ✓ Multiple output formats

## 📝 Example Output

### Extraction Log Example

```
[2025-10-11 14:30:15]
Processed resume_john_doe.pdf: Found 2 emails, 1 phones
Set email to: john.doe@example.com
Set phone to: +855 12 345 678
Other emails found: alternate@example.com
==================================================
```

### Chatter Message Example

```
Contact information automatically extracted from attachments:
• Set email to: john.doe@example.com
• Set phone to: +855 12 345 678
• Other emails found: alternate@example.com
```

## 🚀 Next Steps

After installation:

1. ✅ Run `python3 test_extraction.py`
2. ✅ Restart Odoo server
3. ✅ Upgrade `angkot_recruitement` module
4. ✅ Test with a sample candidate
5. ✅ Configure auto-extract preferences
6. ✅ Train your team on the feature

## 📖 Learn More

- **Quick Start**: This file (README_EXTRACTION.md)
- **Installation**: INSTALLATION_GUIDE.md
- **Full Documentation**: CANDIDATE_EXTRACTION_FEATURE.md
- **Test Your Setup**: `python3 test_extraction.py`

## 🎯 Key Commands

```bash
# Install everything
pip install -r requirements.txt
brew install tesseract poppler  # macOS

# Test installation
python3 test_extraction.py

# Upgrade Odoo module
./odoo-bin -u angkot_recruitement -d your_database
```

## 💡 Tips

- Enable auto-extract by default for new candidates
- Check extraction logs if results seem wrong
- Manual extraction button can reprocess anytime
- Multiple emails/phones are logged in chatter
- OCR works but is slower - use text PDFs when possible

---

**Ready to start?** Run `python3 test_extraction.py` to verify your setup! 🎉


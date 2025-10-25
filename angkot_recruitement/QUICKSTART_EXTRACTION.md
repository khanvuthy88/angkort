# ⚡ Quick Start - Contact Auto-Extraction

Get started with automatic contact extraction in under 5 minutes!

## ✅ Installation (Copy & Paste)

### For macOS (Your System):

```bash
# Step 1: Install Python packages
cd /Users/khanvuthy/Documents/odoo/odoo18-project/angkort/angkot_recruitement
pip install PyPDF2 pdfplumber pdf2image pytesseract python-docx2txt phonenumbers Pillow

# Step 2: Install system dependencies
brew install tesseract poppler

# Step 3: Test installation
python3 test_extraction.py

# Step 4: Restart Odoo and upgrade module
# Then in Odoo UI: Apps > angkot_recruitement > Upgrade
```

### For Ubuntu/Debian:

```bash
# Step 1: Install Python packages
cd /path/to/angkort/angkot_recruitement
pip install PyPDF2 pdfplumber pdf2image pytesseract python-docx2txt phonenumbers Pillow

# Step 2: Install system dependencies
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils

# Step 3: Test installation
python3 test_extraction.py

# Step 4: Restart Odoo and upgrade module
sudo systemctl restart odoo
# Then in Odoo UI: Apps > angkot_recruitement > Upgrade
```

## 🎯 Usage

### Automatic (Recommended)

1. Go to: **Recruitment > Candidates**
2. Create or open a candidate
3. Upload a CV/Resume (PDF, DOCX, TXT)
4. **Done!** Email and phone are extracted automatically ✨

### Manual

1. Open candidate with attachments
2. Click **"Extract Contact Info"** button
3. Check results in "Extraction Log" tab

## 📋 What You Get

| Feature | Description |
|---------|-------------|
| Auto Email | Extracts email from CV automatically |
| Auto Phone | Extracts phone with international format |
| Multiple Methods | PDF → DOCX → TXT support |
| OCR Support | Scans image-based PDFs |
| Smart Filling | Won't overwrite existing data |
| Extraction Logs | See what was found and when |

## 🧪 Quick Test

1. Create a test text file `test_resume.txt`:
```
John Doe
Email: test@example.com
Phone: +855 12 345 678
```

2. Save as PDF or use as TXT
3. Create new candidate in Odoo
4. Upload the file
5. Check if email and phone are filled ✓

## ⚙️ Configuration

On candidate form:
- **Auto-Extract Contact Info**: Toggle ON/OFF (default: ON)
- **Extraction Log**: View extraction history
- **Extract Contact Info** button: Manual trigger

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| No text extracted | Install Tesseract: `brew install tesseract` |
| Phone not found | Install phonenumbers: `pip install phonenumbers` |
| Module won't load | Check logs: `/var/log/odoo/odoo-server.log` |
| Slow extraction | Normal for OCR (5-15 sec), fast for text PDFs (<1 sec) |

## 📊 Verification Checklist

Run this to verify everything works:

```bash
python3 test_extraction.py
```

Expected output:
```
✓ Core functionality ready!
✓ OCR functionality ready!
✅ You can now use the extraction feature!
```

## 🚀 What's Installed

### Files Added:
- ✅ `models/hr_candidate.py` - Main extraction logic
- ✅ `views/hr_candidate_views.xml` - UI enhancements
- ✅ `requirements.txt` - Python dependencies
- ✅ `test_extraction.py` - Test script
- ✅ Documentation files

### Features Added:
- ✅ Auto-extraction toggle per candidate
- ✅ Manual extraction button
- ✅ Extraction log tab
- ✅ Multi-format support (PDF/DOCX/TXT)
- ✅ OCR for scanned documents
- ✅ International phone parsing
- ✅ Chatter integration

## 📚 More Info

| Document | When to Use |
|----------|-------------|
| `QUICKSTART_EXTRACTION.md` | **START HERE** - Quick setup |
| `README_EXTRACTION.md` | Overview and quick reference |
| `INSTALLATION_GUIDE.md` | Detailed installation help |
| `CANDIDATE_EXTRACTION_FEATURE.md` | Complete documentation |
| `test_extraction.py` | Verify dependencies |

## 💡 Pro Tips

1. **Use text-based PDFs** when possible (much faster than OCR)
2. **Check extraction logs** if results seem wrong
3. **Enable auto-extract** for most candidates (default)
4. **Disable for special cases** where you want manual control
5. **OCR processes first 3 pages** to avoid slowness

## 🎯 Common Workflows

### New Candidate with CV
```
1. Click "Create" in Candidates
2. Attach CV file
3. Save
4. Email/Phone auto-filled! ✓
```

### Existing Candidate
```
1. Open candidate
2. Attach CV file
3. Email/Phone auto-filled if empty
4. Or click "Extract Contact Info" to reprocess
```

### Batch Processing
```
1. Import candidates
2. Attach CVs via UI or script
3. Auto-extraction runs for each
4. Review extraction logs for any issues
```

## ✅ You're Ready!

Next steps:
1. ✅ Run `python3 test_extraction.py`
2. ✅ Restart Odoo
3. ✅ Upgrade module
4. ✅ Test with a real CV
5. ✅ Enjoy automated contact extraction! 🎉

---

**Need Help?** Check `INSTALLATION_GUIDE.md` or `CANDIDATE_EXTRACTION_FEATURE.md`

**Issues?** Run `python3 test_extraction.py` to diagnose


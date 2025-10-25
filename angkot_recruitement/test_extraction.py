#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for candidate contact information extraction feature.
Run this script to verify all dependencies are installed correctly.

Usage: python3 test_extraction.py
"""

import sys
import io

def test_imports():
    """Test if all required packages can be imported."""
    print("=" * 60)
    print("TESTING PACKAGE IMPORTS")
    print("=" * 60)
    
    results = {
        'required': [],
        'optional': [],
        'failed': []
    }
    
    # Required packages
    required_packages = [
        ('PyPDF2', 'PyPDF2'),
        ('pdfplumber', 'pdfplumber'),
        ('docx2txt', 'python-docx2txt'),
        ('phonenumbers', 'phonenumbers'),
    ]
    
    # Optional packages (for OCR)
    optional_packages = [
        ('pdf2image', 'pdf2image'),
        ('pytesseract', 'pytesseract'),
        ('PIL', 'Pillow'),
    ]
    
    print("\n📦 Required Packages:")
    for pkg, pip_name in required_packages:
        try:
            __import__(pkg)
            print(f"  ✓ {pip_name}")
            results['required'].append((pip_name, True))
        except ImportError:
            print(f"  ✗ {pip_name} - Install: pip install {pip_name}")
            results['required'].append((pip_name, False))
            results['failed'].append(pip_name)
    
    print("\n📦 Optional Packages (for OCR):")
    for pkg, pip_name in optional_packages:
        try:
            __import__(pkg)
            print(f"  ✓ {pip_name}")
            results['optional'].append((pip_name, True))
        except ImportError:
            print(f"  ⚠ {pip_name} - Install: pip install {pip_name}")
            results['optional'].append((pip_name, False))
    
    return results

def test_system_dependencies():
    """Test if system dependencies (Tesseract, Poppler) are installed."""
    print("\n" + "=" * 60)
    print("TESTING SYSTEM DEPENDENCIES")
    print("=" * 60)
    
    import subprocess
    
    results = []
    
    # Test Tesseract
    print("\n🔧 Tesseract OCR:")
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"  ✓ Installed: {version}")
            results.append(('tesseract', True))
        else:
            print(f"  ✗ Not working properly")
            results.append(('tesseract', False))
    except FileNotFoundError:
        print(f"  ✗ Not installed")
        print(f"     macOS: brew install tesseract")
        print(f"     Ubuntu: sudo apt-get install tesseract-ocr")
        results.append(('tesseract', False))
    except subprocess.TimeoutExpired:
        print(f"  ⚠ Command timed out")
        results.append(('tesseract', False))
    
    # Test Poppler
    print("\n🔧 Poppler (pdfinfo):")
    try:
        result = subprocess.run(['pdfinfo', '-v'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0] if result.stdout else result.stderr.split('\n')[0]
            print(f"  ✓ Installed: {version}")
            results.append(('poppler', True))
        else:
            print(f"  ✗ Not working properly")
            results.append(('poppler', False))
    except FileNotFoundError:
        print(f"  ✗ Not installed")
        print(f"     macOS: brew install poppler")
        print(f"     Ubuntu: sudo apt-get install poppler-utils")
        results.append(('poppler', False))
    except subprocess.TimeoutExpired:
        print(f"  ⚠ Command timed out")
        results.append(('poppler', False))
    
    return results

def test_extraction_functions():
    """Test basic extraction functionality."""
    print("\n" + "=" * 60)
    print("TESTING EXTRACTION FUNCTIONS")
    print("=" * 60)
    
    # Test email extraction
    print("\n📧 Email Extraction:")
    test_text = """
    John Doe
    Email: john.doe@example.com
    Contact: jane.smith@company.co.uk
    Backup: support+test@example.org
    """
    
    import re
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, test_text, re.IGNORECASE)
    
    if emails:
        print(f"  ✓ Found {len(emails)} email(s):")
        for email in emails:
            print(f"    - {email}")
    else:
        print(f"  ✗ No emails found")
    
    # Test phone extraction
    print("\n📱 Phone Number Extraction:")
    test_phone_text = """
    Phone: +855 12 345 678
    Mobile: (123) 456-7890
    Office: 012-345-678
    """
    
    try:
        import phonenumbers
        print("  Using phonenumbers library:")
        
        found_phones = []
        for match in phonenumbers.PhoneNumberMatcher(test_phone_text, "KH"):
            formatted = phonenumbers.format_number(
                match.number, 
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            found_phones.append(formatted)
        
        if found_phones:
            print(f"  ✓ Found {len(found_phones)} phone number(s):")
            for phone in found_phones:
                print(f"    - {phone}")
        else:
            print(f"  ⚠ No phones found with phonenumbers lib, trying regex...")
    except ImportError:
        print("  Using regex fallback:")
    
    # Regex fallback
    phone_patterns = [
        r'\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
    ]
    
    for pattern in phone_patterns:
        phones = re.findall(pattern, test_phone_text)
        if phones:
            print(f"  ✓ Found {len(phones)} phone pattern(s):")
            for phone in phones:
                print(f"    - {phone.strip()}")
            break

def test_pdf_extraction():
    """Test PDF text extraction with a simple PDF."""
    print("\n" + "=" * 60)
    print("TESTING PDF EXTRACTION")
    print("=" * 60)
    
    print("\n📄 Creating test PDF in memory...")
    
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # Create a simple PDF in memory
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Test Resume")
        c.drawString(100, 730, "Name: John Doe")
        c.drawString(100, 710, "Email: john.doe@test.com")
        c.drawString(100, 690, "Phone: +855 12 345 678")
        c.save()
        
        pdf_content = buffer.getvalue()
        buffer.close()
        
        print("  ✓ Test PDF created")
        
        # Try to extract text
        print("\n📖 Testing text extraction:")
        
        # Test with pdfplumber
        try:
            import pdfplumber
            pdf_file = io.BytesIO(pdf_content)
            with pdfplumber.open(pdf_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            
            if text.strip():
                print(f"  ✓ pdfplumber: Extracted {len(text)} characters")
                if "john.doe@test.com" in text.lower():
                    print(f"    ✓ Email found in extracted text")
                else:
                    print(f"    ⚠ Email not found in extracted text")
            else:
                print(f"  ⚠ pdfplumber: No text extracted")
        except Exception as e:
            print(f"  ✗ pdfplumber: {str(e)}")
        
        # Test with PyPDF2
        try:
            import PyPDF2
            pdf_file = io.BytesIO(pdf_content)
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            
            if text.strip():
                print(f"  ✓ PyPDF2: Extracted {len(text)} characters")
            else:
                print(f"  ⚠ PyPDF2: No text extracted")
        except Exception as e:
            print(f"  ✗ PyPDF2: {str(e)}")
            
    except ImportError:
        print("  ⚠ reportlab not installed (optional for this test)")
        print("     Skipping PDF creation test")
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")

def print_summary(import_results, system_results):
    """Print summary of test results."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    required_passed = all(result[1] for result in import_results['required'])
    optional_passed = all(result[1] for result in import_results['optional'])
    system_passed = all(result[1] for result in system_results)
    
    print("\n✅ Required Packages:", "ALL OK" if required_passed else "MISSING")
    if not required_passed:
        print("   Missing:", ", ".join(import_results['failed']))
        print("   Install: pip install -r requirements.txt")
    
    print("\n⚙️  Optional Packages (OCR):", "ALL OK" if optional_passed else "SOME MISSING")
    if not optional_passed:
        missing = [r[0] for r in import_results['optional'] if not r[1]]
        print("   Missing:", ", ".join(missing))
        print("   Note: OCR features will not work without these")
    
    print("\n🔧 System Dependencies:", "ALL OK" if system_passed else "SOME MISSING")
    if not system_passed:
        missing = [r[0] for r in system_results if not r[1]]
        print("   Missing:", ", ".join(missing))
    
    print("\n" + "=" * 60)
    
    if required_passed:
        print("✓ Core functionality ready!")
        if optional_passed and system_passed:
            print("✓ OCR functionality ready!")
        else:
            print("⚠ OCR functionality limited (missing optional packages)")
        print("\n✅ You can now use the extraction feature!")
        print("   Next: Restart Odoo and upgrade the angkot_recruitement module")
    else:
        print("✗ Please install missing required packages")
        print("   Run: pip install -r requirements.txt")
    
    print("=" * 60)

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("CANDIDATE EXTRACTION FEATURE - DEPENDENCY TEST")
    print("=" * 60)
    print("\nThis script will test if all dependencies are properly installed.")
    print("This does NOT require Odoo to be running.\n")
    
    import_results = test_imports()
    system_results = test_system_dependencies()
    
    if all(r[1] for r in import_results['required']):
        test_extraction_functions()
        test_pdf_extraction()
    
    print_summary(import_results, system_results)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


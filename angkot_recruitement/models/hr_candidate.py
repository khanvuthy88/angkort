# -*- coding: utf-8 -*-

import base64
import re
import io
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Try to import required libraries
try:
    import PyPDF2
    import pdfplumber
except ImportError:
    PyPDF2 = None
    pdfplumber = None
    _logger.warning("PyPDF2 or pdfplumber not installed. PDF text extraction will be limited.")

try:
    from pdf2image import convert_from_bytes
    import pytesseract
except ImportError:
    convert_from_bytes = None
    pytesseract = None
    _logger.warning("pdf2image or pytesseract not installed. OCR functionality will not be available.")

try:
    import docx2txt
except ImportError:
    docx2txt = None
    _logger.warning("docx2txt not installed. DOCX extraction will not be available.")

try:
    import phonenumbers
    from phonenumbers import NumberParseException
except ImportError:
    phonenumbers = None
    _logger.warning("phonenumbers not installed. Phone number validation will be limited.")


class HrCandidate(models.Model):
    _inherit = 'hr.candidate'

    # Auto-extraction fields
    auto_extract_enabled = fields.Boolean(
        string="Auto-Extract Contact Info",
        default=True,
        help="Automatically extract email and phone from uploaded documents"
    )
    last_extraction_date = fields.Datetime(
        string="Last Extraction Date",
        readonly=True,
        help="Last time contact information was extracted from attachments"
    )
    extraction_log = fields.Text(
        string="Extraction Log",
        readonly=True,
        help="Log of extraction attempts and results"
    )

    user_id = fields.Many2one('res.users')
    # Profile sections
    education_ids = fields.One2many(
        'hr.candidate.education',
        'candidate_id',
        string='Education'
    )
    experience_ids = fields.One2many(
        'hr.candidate.experience',
        'candidate_id',
        string='Work Experience'
    )
    certification_ids = fields.One2many(
        'hr.candidate.certification',
        'candidate_id',
        string='Certifications'
    )
    portfolio_ids = fields.One2many(
        'hr.candidate.portfolio',
        'candidate_id',
        string='Portfolio'
    )
    
    # Counts for smart buttons
    education_count = fields.Integer(
        string='Education Count',
        compute='_compute_profile_counts'
    )
    experience_count = fields.Integer(
        string='Experience Count',
        compute='_compute_profile_counts'
    )
    certification_count = fields.Integer(
        string='Certification Count',
        compute='_compute_profile_counts'
    )
    portfolio_count = fields.Integer(
        string='Portfolio Count',
        compute='_compute_profile_counts'
    )
    total_experience_months = fields.Integer(
        string='Total Experience (Months)',
        compute='_compute_total_experience'
    )
    
    def _compute_profile_counts(self):
        for candidate in self:
            candidate.education_count = len(candidate.education_ids)
            candidate.experience_count = len(candidate.experience_ids)
            candidate.certification_count = len(candidate.certification_ids)
            candidate.portfolio_count = len(candidate.portfolio_ids)
    
    def _compute_total_experience(self):
        for candidate in self:
            total = sum(exp.duration_months for exp in candidate.experience_ids)
            candidate.total_experience_months = total

    def unlink(self):
        """Override unlink to handle candidates with applicants gracefully."""
        for candidate in self:
            # Check if there are any applicants linked to this candidate
            applicants = self.env['hr.applicant'].search([
                ('candidate_id', '=', candidate.id)
            ])
            
            if applicants:
                # Get job titles for better error message
                job_titles = ', '.join(applicants.mapped('job_id.name')[:3])
                if len(applicants) > 3:
                    job_titles += f', and {len(applicants) - 3} more'
                
                raise UserError(
                    _("Cannot delete candidate '%s' because there are %d job application(s) linked to this candidate "
                      "(Jobs: %s).\n\n"
                      "Please consider archiving the candidate instead, or delete the related applications first.") 
                    % (candidate.partner_name or candidate.email_from, len(applicants), job_titles)
                )
        
        return super(HrCandidate, self).unlink()

    def action_archive_with_applicants(self):
        """Archive candidate along with all related applicants."""
        self.ensure_one()
        
        # Find all related applicants
        applicants = self.env['hr.applicant'].search([
            ('candidate_id', '=', self.id)
        ])
        
        # Archive the candidate and applicants
        if applicants:
            applicants.write({'active': False})
            self.active = False
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Archived Successfully'),
                    'message': _('Candidate and %d related application(s) have been archived.') % len(applicants),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            # No applicants, just archive the candidate
            self.active = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Archived Successfully'),
                    'message': _('Candidate has been archived.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def _extract_text_from_pdf(self, file_content):
        """Extract text from PDF using multiple methods."""
        text = ""
        
        # Method 1: Try pdfplumber first (usually better results)
        if pdfplumber:
            try:
                pdf_file = io.BytesIO(file_content)
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                if text.strip():
                    _logger.info("Successfully extracted text using pdfplumber")
                    return text
            except Exception as e:
                _logger.warning(f"pdfplumber extraction failed: {str(e)}")
        
        # Method 2: Try PyPDF2
        if PyPDF2 and not text.strip():
            try:
                pdf_file = io.BytesIO(file_content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                if text.strip():
                    _logger.info("Successfully extracted text using PyPDF2")
                    return text
            except Exception as e:
                _logger.warning(f"PyPDF2 extraction failed: {str(e)}")
        
        # Method 3: OCR as fallback (for scanned PDFs)
        if convert_from_bytes and pytesseract and not text.strip():
            try:
                _logger.info("Attempting OCR extraction...")
                images = convert_from_bytes(file_content, dpi=300, first_page=1, last_page=3)
                for i, image in enumerate(images):
                    ocr_text = pytesseract.image_to_string(image, lang='eng')
                    if ocr_text:
                        text += ocr_text + "\n"
                if text.strip():
                    _logger.info("Successfully extracted text using OCR")
                    return text
            except Exception as e:
                _logger.warning(f"OCR extraction failed: {str(e)}")
        
        return text

    def _extract_text_from_docx(self, file_content):
        """Extract text from DOCX files."""
        if not docx2txt:
            _logger.warning("docx2txt not available")
            return ""
        
        try:
            text = docx2txt.process(io.BytesIO(file_content))
            _logger.info("Successfully extracted text from DOCX")
            return text
        except Exception as e:
            _logger.warning(f"DOCX extraction failed: {str(e)}")
            return ""

    def _extract_text_from_txt(self, file_content):
        """Extract text from plain text files."""
        try:
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    text = file_content.decode(encoding)
                    _logger.info(f"Successfully extracted text from TXT (encoding: {encoding})")
                    return text
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            _logger.warning(f"TXT extraction failed: {str(e)}")
        return ""

    def _extract_emails_from_text(self, text):
        """Extract email addresses from text using regex."""
        if not text:
            return []
        
        # Enhanced email regex pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text, re.IGNORECASE)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_emails = []
        for email in emails:
            email_lower = email.lower()
            if email_lower not in seen:
                seen.add(email_lower)
                unique_emails.append(email)
        
        return unique_emails

    def _extract_phone_numbers_from_text(self, text, region='KH'):
        """Extract phone numbers from text."""
        if not text:
            return []
        
        phone_numbers = []
        
        # If phonenumbers library is available, use it for better parsing
        if phonenumbers:
            try:
                # Find all potential phone numbers
                for match in phonenumbers.PhoneNumberMatcher(text, region):
                    phone_numbers.append(phonenumbers.format_number(
                        match.number, 
                        phonenumbers.PhoneNumberFormat.INTERNATIONAL
                    ))
            except Exception as e:
                _logger.warning(f"phonenumbers extraction failed: {str(e)}")
        
        # Fallback regex patterns for common formats
        if not phone_numbers:
            # Patterns for various phone formats
            patterns = [
                r'\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US/Standard format
                r'\d{3}[-.\s]?\d{3}[-.\s]?\d{3,4}',  # Simple format
                r'\+855[-.\s]?\d{1,2}[-.\s]?\d{3}[-.\s]?\d{3,4}',  # Cambodia format
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                phone_numbers.extend(matches)
        
        # Clean and deduplicate
        cleaned_phones = []
        seen = set()
        for phone in phone_numbers:
            # Remove extra spaces and normalize
            cleaned = re.sub(r'\s+', ' ', phone.strip())
            if cleaned and cleaned not in seen and len(re.sub(r'\D', '', cleaned)) >= 7:
                seen.add(cleaned)
                cleaned_phones.append(cleaned)
        
        return cleaned_phones

    def _extract_name_from_attachments(self, candidate_id):
        """Extract candidate name from resume attachments."""
        try:
            # Get attachments for this candidate
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'hr.candidate'),
                ('res_id', '=', candidate_id),
                ('mimetype', '=', 'application/pdf')
            ])
            
            if not attachments:
                return None
            
            # Extract text from the first PDF attachment
            for attachment in attachments:
                if attachment.datas:
                    # Decode base64 data
                    file_content = base64.b64decode(attachment.datas)
                    
                    # Extract text from PDF
                    text = self._extract_text_from_pdf(file_content)
                    if text:
                        _logger.info(f"Extracted text from PDF (first 500 chars): {text[:500]}")
                        _logger.info(f"Extracted text from PDF (full text): {text}")
                        # Try to extract name from text
                        name = self._extract_name_from_text(text)
                        if name:
                            _logger.info(f"Successfully extracted name: {name}")
                            return name
                        else:
                            _logger.warning("Could not extract name from PDF text")
                            _logger.info(f"First 20 lines of text: {text.split('\\n')[:20]}")
                    else:
                        _logger.warning("Could not extract text from PDF")
            
            return None
        except Exception as e:
            _logger.warning(f"Error extracting name from attachments: {e}")
            return None

    def _extract_name_from_text(self, text):
        """Extract candidate name from resume text."""
        try:
            # Common patterns for names in resumes
            lines = text.split('\n')
            
            # Look for name in first few lines (usually at the top of resume)
            for i, line in enumerate(lines[:15]):  # Check first 15 lines
                line = line.strip()
                if not line:
                    continue
                
                # Skip lines that are clearly not names
                if any(skip_word in line.lower() for skip_word in 
                      ['email', 'phone', 'address', 'objective', 'summary', 'experience', 
                       'education', 'skills', 'resume', 'cv', 'contact', 'profile', 'developer', 'engineer']):
                    continue
                
                # Check if line looks like a name (2-5 words, starts with capital letter)
                words = line.split()
                if 2 <= len(words) <= 5:
                    # All words should start with capital letters and contain only letters
                    # Allow for some special characters like hyphens and apostrophes
                    if all(word[0].isupper() and word.replace('-', '').replace("'", '').replace('.', '').isalpha() 
                           for word in words if word):
                        # Additional validation: not too long, no digits, reasonable length
                        if len(line) <= 60 and not any(char.isdigit() for char in line):
                            # Extra validation: should contain at least one space (first name + last name)
                            if ' ' in line and len(line) >= 3:
                                _logger.info(f"Found potential name in line {i+1}: {line}")
                                return line
            
            # Try to find name patterns in the text using regex
            import re
            
            # Pattern for names like "KHAN VUTHY" or "John Smith"
            name_patterns = [
                r'^([A-Z]{2,}\s[A-Z]{2,}(?:\s[A-Z]{2,})*)$',  # All caps names like "KHAN VUTHY"
                r'^([A-Z][a-z]+ [A-Z][a-z]+(?:\s[A-Z][a-z]+)*)$',  # Proper case names
                r'^([A-Z][a-z]+\s[A-Z][a-z]+)$',  # Simple two-word names
                r'^([A-Z][A-Z\s]{2,40})$',  # Any all-caps text (fallback)
            ]
            
            for pattern in name_patterns:
                for line in lines[:15]:
                    line = line.strip()
                    match = re.match(pattern, line)
                    if match:
                        name = match.group(1).strip()
                        # Skip if it's clearly not a name
                        if not any(skip_word in name.lower() for skip_word in 
                                  ['email', 'phone', 'address', 'objective', 'summary', 'experience', 
                                   'education', 'skills', 'resume', 'cv', 'contact', 'profile', 'developer', 'engineer']):
                            _logger.info(f"Found name using pattern '{pattern}': {name}")
                            return name
            
            # If no clear name found, try email-based extraction as fallback
            emails = self._extract_emails_from_text(text)
            if emails:
                email_name = emails[0].split('@')[0]
                # Clean up email name
                name_parts = email_name.replace('.', ' ').replace('_', ' ').replace('-', ' ').split()
                if len(name_parts) >= 2:
                    return ' '.join(word.title() for word in name_parts if word.isalpha())
            
            return None
        except Exception as e:
            _logger.warning(f"Error extracting name from text: {e}")
            return None

    def _extract_contact_info_from_attachment(self, attachment):
        """Extract email and phone from a single attachment."""
        result = {
            'emails': [],
            'phones': [],
            'success': False,
            'message': ''
        }
        
        try:
            # Decode attachment content
            file_content = base64.b64decode(attachment.datas)
            file_name = attachment.name.lower()
            text = ""
            
            # Extract text based on file type
            if file_name.endswith('.pdf'):
                text = self._extract_text_from_pdf(file_content)
            elif file_name.endswith(('.docx', '.doc')):
                text = self._extract_text_from_docx(file_content)
            elif file_name.endswith('.txt'):
                text = self._extract_text_from_txt(file_content)
            else:
                result['message'] = f"Unsupported file type: {file_name}"
                return result
            
            if not text or not text.strip():
                result['message'] = f"No text could be extracted from {file_name}"
                return result
            
            # Extract emails and phones
            result['emails'] = self._extract_emails_from_text(text)
            
            # Try to get region from company
            region = 'KH'  # Default to Cambodia
            if self.company_id and self.company_id.country_id:
                region = self.company_id.country_id.code or 'KH'
            
            result['phones'] = self._extract_phone_numbers_from_text(text, region)
            result['success'] = True
            result['message'] = f"Processed {file_name}: Found {len(result['emails'])} emails, {len(result['phones'])} phones"
            
        except Exception as e:
            result['message'] = f"Error processing {attachment.name}: {str(e)}"
            _logger.error(result['message'])
        
        return result

    def _update_candidate_contact_info(self, emails, phones):
        """Update candidate with extracted contact information."""
        updated = False
        log_messages = []
        
        for candidate in self:
            # Update email if not set OR if it's a temporary email
            is_temp_email = candidate.email_from and '@pending-extraction.local' in candidate.email_from
            if emails and (not candidate.email_from or is_temp_email):
                old_email = candidate.email_from
                candidate.email_from = emails[0]
                updated = True
                if is_temp_email:
                    log_messages.append(f"Replaced temporary email with: {emails[0]}")
                else:
                    log_messages.append(f"Set email to: {emails[0]}")
                if len(emails) > 1:
                    log_messages.append(f"Other emails found: {', '.join(emails[1:])}")
            
            # Update partner_name if it's a temporary name
            is_temp_name = (candidate.partner_name and 
                           ('Candidate from Resume' in candidate.partner_name or 
                            'Candidate - ' in candidate.partner_name))
            if is_temp_name:
                _logger.info(f"Detected temporary name: {candidate.partner_name}")
                # Try to extract name from PDF content first
                extracted_name = self._extract_name_from_attachments(candidate.id)
                if extracted_name:
                    candidate.partner_name = extracted_name
                    updated = True
                    log_messages.append(f"Updated candidate name from resume: {extracted_name}")
                    _logger.info(f"Successfully extracted name: {extracted_name}")
                elif candidate.email_from and not is_temp_email:
                    # Fallback: Extract name from email (before @)
                    name_from_email = candidate.email_from.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                    candidate.partner_name = name_from_email
                    updated = True
                    log_messages.append(f"Updated candidate name from email: {name_from_email}")
                    _logger.info(f"Fallback to email-based name: {name_from_email}")
                else:
                    _logger.warning(f"Could not extract name for candidate {candidate.id}")
                    log_messages.append("Could not extract candidate name from resume or email")
            
            # Update phone if not set and we found one
            if phones and not candidate.partner_phone:
                candidate.partner_phone = phones[0]
                updated = True
                log_messages.append(f"Set phone to: {phones[0]}")
                if len(phones) > 1:
                    log_messages.append(f"Other phones found: {', '.join(phones[1:])}")
            
            if updated:
                candidate.last_extraction_date = fields.Datetime.now()
                candidate.message_post(
                    body=_("Contact information automatically extracted from attachments:<br/>%s") % 
                         "<br/>".join(log_messages),
                    subject=_("Auto-extracted Contact Information")
                )
        
        return updated, log_messages

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to extract contact info from attachments."""
        candidates = super(HrCandidate, self).create(vals_list)
        
        for candidate in candidates:
            if candidate.auto_extract_enabled:
                candidate._auto_extract_from_attachments()
        
        return candidates

    def write(self, vals):
        """Override write to extract contact info when attachments are added."""
        result = super(HrCandidate, self).write(vals)
        
        # If attachments might have been added, trigger extraction
        if self.auto_extract_enabled and not self.env.context.get('skip_auto_extract'):
            # Check if we should extract (e.g., missing contact info)
            for candidate in self:
                if not candidate.email_from or not candidate.partner_phone:
                    candidate._auto_extract_from_attachments()
        
        return result

    def create_employee_from_candidate(self):
        """Override to create proper candidate contact with clear identification."""
        self.ensure_one()
        self._check_interviewer_access()

        if not self.partner_id:
            if not self.partner_name:
                raise UserError(_('Please provide a candidate name.'))
            
            # Create candidate contact with proper identification
            self.partner_id = self.env['res.partner'].create(self._get_candidate_contact_vals())

        action = self.env['ir.actions.act_window']._for_xml_id('hr.open_view_employee_list')
        employee = self.env['hr.employee'].create(self._get_employee_create_vals())
        action['res_id'] = employee.id
        return action

    def _get_candidate_contact_vals(self):
        """Get values for creating a candidate contact (res.partner)."""
        self.ensure_one()
        
        # Get or create candidate category
        candidate_category = self._get_or_create_candidate_category()
        
        vals = {
            'is_company': False,
            'name': self.partner_name,
            'email': self.email_from,
            'phone': self.partner_phone,
            'mobile': self.partner_phone,  # Also set mobile for consistency
            'category_id': [(6, 0, [candidate_category.id])],
            'comment': f"Contact created from candidate: {self.partner_name}\n"
                      f"Original candidate ID: {self.id}\n"
                      f"Created on: {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'user_id': self.user_id.id if self.user_id else False,
            'company_id': self.company_id.id if self.company_id else False,
        }
        
        # Add LinkedIn profile if available
        if self.linkedin_profile:
            vals['website'] = self.linkedin_profile
            vals['comment'] += f"\nLinkedIn: {self.linkedin_profile}"
        
        # Add candidate-specific custom fields if they exist
        if hasattr(self, 'candidate_properties') and self.candidate_properties:
            vals['comment'] += f"\nCandidate Properties: {self.candidate_properties}"
        
        return vals

    def _get_or_create_candidate_category(self):
        """Get or create a category for candidate contacts."""
        # Look for existing candidate category
        candidate_category = self.env['res.partner.category'].search([
            ('name', '=', 'Candidate Contact')
        ], limit=1)
        
        if not candidate_category:
            # Create candidate category
            candidate_category = self.env['res.partner.category'].create({
                'name': 'Candidate Contact',
                'color': 2,  # Blue color
            })
        
        return candidate_category

    def action_create_candidate_contact(self):
        """Create a candidate contact (res.partner) without creating an employee."""
        self.ensure_one()
        
        if self.partner_id:
            raise UserError(_('This candidate already has a contact record.'))
        
        if not self.partner_name:
            raise UserError(_('Please provide a candidate name.'))
        
        # Create candidate contact
        partner_vals = self._get_candidate_contact_vals()
        partner = self.env['res.partner'].create(partner_vals)
        
        # Link the partner to the candidate
        self.partner_id = partner.id
        
        # Post message to candidate chatter
        self.message_post(
            body=_("Candidate contact created: <a href='#id=%d&model=res.partner'>%s</a>") % (partner.id, partner.name),
            subject=_("Contact Created")
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Candidate Contact'),
            'res_model': 'res.partner',
            'res_id': partner.id,
            'view_mode': 'form',
            'target': 'current',
        }


    def _auto_extract_from_attachments(self):
        """Automatically extract contact info from all attachments."""
        self.ensure_one()
        
        if not self.auto_extract_enabled:
            return
        
        # Get all attachments for this candidate
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.candidate'),
            ('res_id', '=', self.id),
            ('mimetype', 'in', [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/msword',
                'text/plain'
            ])
        ])
        
        if not attachments:
            _logger.info(f"No suitable attachments found for candidate {self.id}")
            return
        
        all_emails = []
        all_phones = []
        extraction_logs = []
        
        for attachment in attachments:
            result = self._extract_contact_info_from_attachment(attachment)
            extraction_logs.append(result['message'])
            
            if result['success']:
                all_emails.extend(result['emails'])
                all_phones.extend(result['phones'])
        
        # Remove duplicates
        all_emails = list(dict.fromkeys(all_emails))
        all_phones = list(dict.fromkeys(all_phones))
        
        # Update candidate
        if all_emails or all_phones:
            updated, log_messages = self._update_candidate_contact_info(all_emails, all_phones)
            extraction_logs.extend(log_messages)
        
        # Store extraction log
        self.extraction_log = "\n".join([
            f"[{fields.Datetime.now()}]",
            *extraction_logs,
            "=" * 50
        ])
        
        _logger.info(f"Extraction completed for candidate {self.id}: {len(all_emails)} emails, {len(all_phones)} phones found")

    def action_extract_contact_info(self):
        """Manual action to extract contact info from attachments."""
        self.ensure_one()
        
        # Force extraction even if fields are already filled
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.candidate'),
            ('res_id', '=', self.id),
        ])
        
        if not attachments:
            raise UserError(_("No attachments found for this candidate."))
        
        self._auto_extract_from_attachments()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Extraction Complete'),
                'message': _('Contact information has been extracted from attachments.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_extraction_log(self):
        """View extraction log in a wizard."""
        self.ensure_one()
        
        return {
            'name': _('Extraction Log'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.candidate',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'show_extraction_log': True}
        }


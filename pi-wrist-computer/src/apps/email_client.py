"""
Email Client Application

Simple IMAP/SMTP email client with:
- Inbox view
- Read emails
- Compose and send
- Multiple accounts
- Gmail OAuth via Device Flow
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
from ..services.google_auth import create_gmail_auth, GoogleDeviceAuth
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.header import decode_header
import json
import os
import threading
from datetime import datetime
import base64
import requests


class EmailApp(App):
    """Email client application."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='email',
            name='Email',
            icon='✉',
            color='#ff6b6b'
        )
        
        # Account settings
        self.accounts = []
        self.current_account = 0
        
        # Email data
        self.emails = []
        self.selected_index = 0
        self.scroll_offset = 0
        
        # State
        self.mode = 'inbox'  # 'inbox', 'read', 'compose', 'login', 'setup'
        self.current_email = None
        self.loading = False
        self.error = None
        
        # Compose state
        self.compose_to = ""
        self.compose_subject = ""
        self.compose_body = ""
        self.compose_field = 0  # 0=to, 1=subject, 2=body
        
        # Login state
        self.login_field = 0  # 0=email, 1=password, 2=provider
        self.login_email = ""
        self.login_password = ""
        self.login_provider = 0  # Index into providers list
        
        # Common email providers
        self.providers = [
            {'name': 'Gmail', 'imap': 'imap.gmail.com', 'smtp': 'smtp.gmail.com'},
            {'name': 'Outlook', 'imap': 'outlook.office365.com', 'smtp': 'smtp.office365.com'},
            {'name': 'Yahoo', 'imap': 'imap.mail.yahoo.com', 'smtp': 'smtp.mail.yahoo.com'},
            {'name': 'iCloud', 'imap': 'imap.mail.me.com', 'smtp': 'smtp.mail.me.com'},
            {'name': 'Custom', 'imap': '', 'smtp': ''},
        ]
        
        # Scroll for reading
        self.read_scroll = 0
        
        # Gmail Device Flow auth
        self.gmail_auth: GoogleDeviceAuth = None
        self.gmail_user_code = ""
        self.gmail_verification_url = ""
        self.gmail_auth_status = ""
        
        self._load_accounts()
        self._init_gmail_auth()
    
    def _init_gmail_auth(self):
        """Initialize Gmail OAuth via Device Flow."""
        self.gmail_auth = create_gmail_auth(
            on_code_received=self._on_gmail_code,
            on_auth_complete=self._on_gmail_auth_complete,
            on_auth_error=self._on_gmail_auth_error
        )
    
    def _on_gmail_code(self, user_code: str, verification_url: str):
        """Called when device code is ready."""
        self.gmail_user_code = user_code
        self.gmail_verification_url = verification_url
        self.gmail_auth_status = "Enter code"
        self.mode = 'gmail_auth'
    
    def _on_gmail_auth_complete(self, token_data: dict):
        """Called when Gmail auth completes."""
        self.gmail_auth_status = "Connected!"
        
        # Add Gmail as an account (OAuth-based)
        gmail_account = {
            'email': 'Gmail (OAuth)',
            'password': '',  # Not needed for OAuth
            'imap_server': 'imap.gmail.com',
            'smtp_server': 'smtp.gmail.com',
            'imap_port': 993,
            'smtp_port': 587,
            'oauth': True  # Mark as OAuth account
        }
        
        # Check if already exists
        exists = any(a.get('oauth') for a in self.accounts)
        if not exists:
            self.accounts.append(gmail_account)
            self._save_accounts()
        
        self.mode = 'inbox'
        self._fetch_gmail_emails()
    
    def _on_gmail_auth_error(self, error: str):
        """Called on Gmail auth error."""
        self.gmail_auth_status = f"Error: {error[:25]}"
        self.error = error
        self.mode = 'login'
    
    def _start_gmail_auth(self):
        """Start Gmail Device Flow authentication."""
        if self.gmail_auth is None:
            self._init_gmail_auth()
        
        if self.gmail_auth:
            self.gmail_auth_status = "Starting..."
            self.gmail_auth.start_auth()
    
    def _fetch_gmail_emails(self):
        """Fetch emails using Gmail API."""
        if not self.gmail_auth or not self.gmail_auth.is_authenticated():
            self.error = "Gmail not connected"
            return
        
        self.loading = True
        thread = threading.Thread(target=self._fetch_gmail_thread)
        thread.daemon = True
        thread.start()
    
    def _fetch_gmail_thread(self):
        """Background Gmail fetch using API."""
        try:
            access_token = self.gmail_auth.get_access_token()
            if not access_token:
                self.error = "No access token"
                return
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Get list of messages
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            params = {"maxResults": 20, "labelIds": "INBOX"}
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 401:
                if self.gmail_auth.refresh_token():
                    self._fetch_gmail_thread()
                else:
                    self.error = "Auth expired"
                return
            
            if response.status_code != 200:
                self.error = f"API error: {response.status_code}"
                return
            
            data = response.json()
            messages = data.get('messages', [])
            
            self.emails = []
            
            # Get details for each message
            for msg in messages[:15]:  # Limit to 15
                msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg['id']}"
                msg_response = requests.get(msg_url, headers=headers, params={"format": "full"})
                
                if msg_response.status_code != 200:
                    continue
                
                msg_data = msg_response.json()
                payload = msg_data.get('payload', {})
                headers_list = payload.get('headers', [])
                
                # Extract headers
                from_addr = ""
                subject = ""
                date_str = ""
                
                for h in headers_list:
                    name = h.get('name', '').lower()
                    if name == 'from':
                        from_addr = h.get('value', '')
                    elif name == 'subject':
                        subject = h.get('value', '')
                    elif name == 'date':
                        date_str = h.get('value', '')
                
                # Get body
                body = ""
                parts = payload.get('parts', [])
                if parts:
                    for part in parts:
                        if part.get('mimeType') == 'text/plain':
                            body_data = part.get('body', {}).get('data', '')
                            if body_data:
                                body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                            break
                else:
                    body_data = payload.get('body', {}).get('data', '')
                    if body_data:
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                
                self.emails.append({
                    'id': msg['id'],
                    'from': from_addr or 'Unknown',
                    'subject': subject or '(No subject)',
                    'body': body,
                    'date': date_str
                })
            
        except Exception as e:
            self.error = str(e)[:50]
        finally:
            self.loading = False
    
    def _send_gmail(self):
        """Send email via Gmail API."""
        if not self.gmail_auth or not self.gmail_auth.is_authenticated():
            self.error = "Gmail not connected"
            return
        
        if not self.compose_to or not self.compose_subject:
            self.error = "To and Subject required"
            return
        
        self.loading = True
        thread = threading.Thread(target=self._send_gmail_thread)
        thread.daemon = True
        thread.start()
    
    def _send_gmail_thread(self):
        """Background Gmail send."""
        try:
            access_token = self.gmail_auth.get_access_token()
            if not access_token:
                self.error = "No access token"
                return
            
            # Create message
            message = MIMEText(self.compose_body)
            message['to'] = self.compose_to
            message['subject'] = self.compose_subject
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            response = requests.post(url, headers=headers, json={"raw": raw})
            
            if response.status_code == 200:
                self.compose_to = ""
                self.compose_subject = ""
                self.compose_body = ""
                self.mode = 'inbox'
            else:
                self.error = f"Send failed: {response.status_code}"
            
        except Exception as e:
            self.error = str(e)[:50]
        finally:
            self.loading = False
    
    def _load_accounts(self):
        """Load email accounts from config."""
        config_path = os.path.expanduser('~/.piwrist_email.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.accounts = json.load(f)
        except Exception:
            self.accounts = []
    
    def _save_accounts(self):
        """Save email accounts."""
        config_path = os.path.expanduser('~/.piwrist_email.json')
        try:
            with open(config_path, 'w') as f:
                json.dump(self.accounts, f)
        except Exception:
            pass
    
    def add_account(self, email_addr: str, password: str, 
                    imap_server: str, smtp_server: str,
                    imap_port: int = 993, smtp_port: int = 587):
        """Add an email account."""
        self.accounts.append({
            'email': email_addr,
            'password': password,
            'imap_server': imap_server,
            'smtp_server': smtp_server,
            'imap_port': imap_port,
            'smtp_port': smtp_port
        })
        self._save_accounts()
    
    def on_enter(self):
        """Load inbox on enter."""
        # Check for Gmail OAuth first
        if self.gmail_auth and self.gmail_auth.is_authenticated():
            self._fetch_gmail_emails()
            self.mode = 'inbox'
        elif self.accounts:
            self._fetch_emails()
            self.mode = 'inbox'
        else:
            self.mode = 'login'
            self.login_email = ""
            self.login_password = ""
            self.login_field = 0
    
    def on_exit(self):
        pass
    
    def _fetch_emails(self):
        """Fetch emails from server."""
        if not self.accounts:
            self.error = "No accounts configured"
            return
        
        self.loading = True
        self.error = None
        
        # Run in background
        thread = threading.Thread(target=self._fetch_emails_thread)
        thread.daemon = True
        thread.start()
    
    def _fetch_emails_thread(self):
        """Background email fetch."""
        try:
            account = self.accounts[self.current_account]
            
            # Connect to IMAP
            mail = imaplib.IMAP4_SSL(account['imap_server'], account['imap_port'])
            mail.login(account['email'], account['password'])
            mail.select('INBOX')
            
            # Search for recent emails
            _, message_numbers = mail.search(None, 'ALL')
            email_ids = message_numbers[0].split()[-20:]  # Last 20
            
            self.emails = []
            for email_id in reversed(email_ids):
                _, msg_data = mail.fetch(email_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode subject
                        subject = msg['Subject']
                        if subject:
                            decoded = decode_header(subject)[0]
                            if isinstance(decoded[0], bytes):
                                subject = decoded[0].decode(decoded[1] or 'utf-8')
                            else:
                                subject = decoded[0]
                        
                        # Decode from
                        from_addr = msg['From']
                        if from_addr:
                            decoded = decode_header(from_addr)[0]
                            if isinstance(decoded[0], bytes):
                                from_addr = decoded[0].decode(decoded[1] or 'utf-8')
                            else:
                                from_addr = decoded[0]
                        
                        # Get body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                        
                        # Get date
                        date_str = msg['Date']
                        
                        self.emails.append({
                            'id': email_id.decode(),
                            'from': from_addr or 'Unknown',
                            'subject': subject or '(No subject)',
                            'body': body,
                            'date': date_str
                        })
            
            mail.logout()
            
        except Exception as e:
            self.error = str(e)[:50]
        finally:
            self.loading = False
    
    def _send_email(self):
        """Send composed email."""
        if not self.accounts:
            self.error = "No accounts configured"
            return
        
        if not self.compose_to or not self.compose_subject:
            self.error = "To and Subject required"
            return
        
        self.loading = True
        thread = threading.Thread(target=self._send_email_thread)
        thread.daemon = True
        thread.start()
    
    def _send_email_thread(self):
        """Background email send."""
        try:
            account = self.accounts[self.current_account]
            
            msg = MIMEText(self.compose_body)
            msg['Subject'] = self.compose_subject
            msg['From'] = account['email']
            msg['To'] = self.compose_to
            
            server = smtplib.SMTP(account['smtp_server'], account['smtp_port'])
            server.starttls()
            server.login(account['email'], account['password'])
            server.send_message(msg)
            server.quit()
            
            # Clear compose fields
            self.compose_to = ""
            self.compose_subject = ""
            self.compose_body = ""
            self.mode = 'inbox'
            
        except Exception as e:
            self.error = str(e)[:50]
        finally:
            self.loading = False
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.mode == 'login':
            return self._handle_login_key(event)
        elif self.mode == 'inbox':
            return self._handle_inbox_key(event)
        elif self.mode == 'read':
            return self._handle_read_key(event)
        elif self.mode == 'compose':
            return self._handle_compose_key(event)
        elif self.mode == 'gmail_auth':
            return self._handle_gmail_auth_key(event)
        return False
    
    def _handle_gmail_auth_key(self, event: KeyEvent) -> bool:
        """Handle keys during Gmail auth."""
        if event.code == KeyCode.ESC:
            if self.gmail_auth:
                self.gmail_auth.cancel_auth()
            self.mode = 'login'
            self.gmail_auth_status = "Cancelled"
            return True
        return True
    
    def _handle_login_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            if self.login_field > 0:
                self.login_field -= 1
            return True
        elif event.code == KeyCode.DOWN:
            if self.login_field < 2:
                self.login_field += 1
            return True
        elif event.code == KeyCode.LEFT:
            if self.login_field == 2:  # Provider selection
                self.login_provider = max(0, self.login_provider - 1)
            return True
        elif event.code == KeyCode.RIGHT:
            if self.login_field == 2:  # Provider selection
                self.login_provider = min(len(self.providers) - 1, self.login_provider + 1)
            return True
        elif event.code == KeyCode.ENTER:
            if self.login_field < 2:
                self.login_field += 1
            else:
                # Try to login
                self._try_login()
            return True
        elif event.code == KeyCode.BACKSPACE:
            if self.login_field == 0 and self.login_email:
                self.login_email = self.login_email[:-1]
            elif self.login_field == 1 and self.login_password:
                self.login_password = self.login_password[:-1]
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        elif event.char == 'g' or event.char == 'G':
            # Start Gmail OAuth
            self._start_gmail_auth()
            return True
        elif event.char:
            if self.login_field == 0:
                self.login_email += event.char
            elif self.login_field == 1:
                self.login_password += event.char
            return True
        return False
    
    def _try_login(self):
        """Attempt to login with entered credentials."""
        if not self.login_email or not self.login_password:
            self.error = "Email and password required"
            return
        
        provider = self.providers[self.login_provider]
        
        # Add account
        self.add_account(
            self.login_email,
            self.login_password,
            provider['imap'] or 'imap.gmail.com',
            provider['smtp'] or 'smtp.gmail.com'
        )
        
        # Try to fetch
        self._fetch_emails()
    
    def _handle_inbox_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            if self.selected_index > 0:
                self.selected_index -= 1
            return True
        elif event.code == KeyCode.DOWN:
            if self.selected_index < len(self.emails) - 1:
                self.selected_index += 1
            return True
        elif event.code == KeyCode.ENTER:
            if self.emails:
                self.current_email = self.emails[self.selected_index]
                self.read_scroll = 0
                self.mode = 'read'
            return True
        elif event.char == 'c' or event.char == 'C':
            self.mode = 'compose'
            self.compose_field = 0
            return True
        elif event.char == 'r' or event.char == 'R':
            # Use Gmail API if authenticated, otherwise IMAP
            if self.gmail_auth and self.gmail_auth.is_authenticated():
                self._fetch_gmail_emails()
            else:
                self._fetch_emails()
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        return False
    
    def _handle_read_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            if self.read_scroll > 0:
                self.read_scroll -= 1
            return True
        elif event.code == KeyCode.DOWN:
            self.read_scroll += 1
            return True
        elif event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'inbox'
            return True
        elif event.char == 'r' or event.char == 'R':
            # Reply
            if self.current_email:
                self.compose_to = self.current_email['from']
                self.compose_subject = f"Re: {self.current_email['subject']}"
                self.compose_body = ""
                self.mode = 'compose'
            return True
        return False
    
    def _handle_compose_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.mode = 'inbox'
            return True
        elif event.code == KeyCode.UP:
            if self.compose_field > 0:
                self.compose_field -= 1
            return True
        elif event.code == KeyCode.DOWN:
            if self.compose_field < 2:
                self.compose_field += 1
            return True
        elif event.code == KeyCode.ENTER:
            if self.compose_field < 2:
                self.compose_field += 1
            return True
        elif event.code == KeyCode.BACKSPACE:
            if self.compose_field == 0 and self.compose_to:
                self.compose_to = self.compose_to[:-1]
            elif self.compose_field == 1 and self.compose_subject:
                self.compose_subject = self.compose_subject[:-1]
            elif self.compose_field == 2 and self.compose_body:
                self.compose_body = self.compose_body[:-1]
            return True
        elif event.char:
            if self.compose_field == 0:
                self.compose_to += event.char
            elif self.compose_field == 1:
                self.compose_subject += event.char
            elif self.compose_field == 2:
                self.compose_body += event.char
            return True
        
        # Ctrl+S or F5 to send (use 's' with some modifier conceptually)
        if event.code == KeyCode.F5:
            # Use Gmail API if authenticated, otherwise SMTP
            if self.gmail_auth and self.gmail_auth.is_authenticated():
                self._send_gmail()
            else:
                self._send_email()
            return True
        
        return False
    
    def draw(self, display: Display):
        """Draw email screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a0a1a')
        
        if self.loading:
            display.text(display.width // 2, display.height // 2,
                        'Loading...', 'white', 14, 'mm')
            return
        
        if self.error:
            display.text(display.width // 2, display.height // 2 - 10,
                        'Error', '#ff4444', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 10,
                        self.error, '#888888', 11, 'mm')
            return
        
        if self.mode == 'login':
            self._draw_login(display)
            return
        
        if not self.accounts:
            self.mode = 'login'
            self._draw_login(display)
            return
        
        if self.mode == 'inbox':
            self._draw_inbox(display)
        elif self.mode == 'read':
            self._draw_read(display)
        elif self.mode == 'compose':
            self._draw_compose(display)
        elif self.mode == 'gmail_auth':
            self._draw_gmail_auth(display)
    
    def _draw_inbox(self, display: Display):
        """Draw inbox list."""
        # Header
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, 'Inbox', 'white', 14)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                    'C:Compose R:Refresh', '#666666', 9, 'rt')
        
        if not self.emails:
            display.text(display.width // 2, display.height // 2,
                        'No emails', '#666666', 14, 'mm')
            return
        
        # Email list
        item_height = 45
        start_y = self.ui.STATUS_BAR_HEIGHT + 25
        max_visible = (display.height - start_y) // item_height
        
        for i in range(max_visible):
            idx = self.scroll_offset + i
            if idx >= len(self.emails):
                break
            
            email_item = self.emails[idx]
            y = start_y + i * item_height
            selected = (idx == self.selected_index)
            
            if selected:
                display.rect(5, y, display.width - 10, item_height - 2,
                            fill='#0066cc')
            
            # From (truncated)
            from_str = email_item['from'][:25]
            display.text(10, y + 8, from_str, 'white', 11)
            
            # Subject
            subj = email_item['subject'][:30]
            display.text(10, y + 24, subj, '#aaaaaa', 10)
    
    def _draw_read(self, display: Display):
        """Draw email reader."""
        if not self.current_email:
            return
        
        # Header
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, 'R:Reply', '#666666', 10)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                    'ESC:Back', '#666666', 10, 'rt')
        
        y = self.ui.STATUS_BAR_HEIGHT + 25
        
        # From
        display.text(10, y, f"From: {self.current_email['from'][:30]}", '#888888', 10)
        y += 15
        
        # Subject
        display.text(10, y, self.current_email['subject'][:35], 'white', 12)
        y += 25
        
        # Body
        display.line(10, y, display.width - 10, y, '#333333')
        y += 10
        
        body = self.current_email['body']
        lines = body.split('\n')
        line_height = 14
        max_lines = (display.height - y - 10) // line_height
        
        visible_lines = lines[self.read_scroll:self.read_scroll + max_lines]
        for line in visible_lines:
            display.text(10, y, line[:38], 'white', 11)
            y += line_height
    
    def _draw_compose(self, display: Display):
        """Draw compose screen."""
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, 'Compose', 'white', 14)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                    'F5:Send ESC:Cancel', '#666666', 9, 'rt')
        
        y = self.ui.STATUS_BAR_HEIGHT + 30
        field_height = 30
        
        # To field
        selected = self.compose_field == 0
        display.rect(10, y, display.width - 20, field_height,
                    fill='#1a1a2e' if not selected else '#0a2a4a',
                    color='#333333' if not selected else '#0066cc')
        display.text(15, y + 8, 'To:', '#888888', 10)
        display.text(45, y + 8, self.compose_to or '', 'white', 11)
        y += field_height + 5
        
        # Subject field
        selected = self.compose_field == 1
        display.rect(10, y, display.width - 20, field_height,
                    fill='#1a1a2e' if not selected else '#0a2a4a',
                    color='#333333' if not selected else '#0066cc')
        display.text(15, y + 8, 'Subj:', '#888888', 10)
        display.text(55, y + 8, self.compose_subject[:25] or '', 'white', 11)
        y += field_height + 5
        
        # Body field
        selected = self.compose_field == 2
        body_height = display.height - y - 10
        display.rect(10, y, display.width - 20, body_height,
                    fill='#1a1a2e' if not selected else '#0a2a4a',
                    color='#333333' if not selected else '#0066cc')
        
        # Show body text
        lines = self.compose_body.split('\n')
        line_y = y + 10
        for line in lines[-8:]:  # Show last 8 lines
            display.text(15, line_y, line[:35], 'white', 11)
            line_y += 14
    
    def _draw_login(self, display: Display):
        """Draw login screen."""
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 15,
                    'Email Login', 'white', 16, 'mm')
        
        y = self.ui.STATUS_BAR_HEIGHT + 45
        field_height = 35
        
        # Email field
        selected = self.login_field == 0
        display.rect(10, y, display.width - 20, field_height,
                    fill='#1a1a2e' if not selected else '#0a2a4a',
                    color='#333333' if not selected else '#0066cc')
        display.text(15, y + 5, 'Email:', '#888888', 10)
        email_display = self.login_email[-25:] if len(self.login_email) > 25 else self.login_email
        display.text(15, y + 18, email_display + ('_' if selected else ''), 'white', 11)
        y += field_height + 8
        
        # Password field
        selected = self.login_field == 1
        display.rect(10, y, display.width - 20, field_height,
                    fill='#1a1a2e' if not selected else '#0a2a4a',
                    color='#333333' if not selected else '#0066cc')
        display.text(15, y + 5, 'Password:', '#888888', 10)
        pw_display = '*' * min(len(self.login_password), 20)
        display.text(15, y + 18, pw_display + ('_' if selected else ''), 'white', 11)
        y += field_height + 8
        
        # Provider selector
        selected = self.login_field == 2
        display.rect(10, y, display.width - 20, field_height,
                    fill='#1a1a2e' if not selected else '#0a2a4a',
                    color='#333333' if not selected else '#0066cc')
        display.text(15, y + 5, 'Provider:', '#888888', 10)
        provider_name = self.providers[self.login_provider]['name']
        display.text(15, y + 18, f'◀ {provider_name} ▶', 'white', 11)
        y += field_height + 15
        
        # Login button
        display.rect(50, y, display.width - 100, 30, fill='#0066cc')
        display.text(display.width // 2, y + 15, 'Login (Enter)', 'white', 12, 'mm')
        
        # Note about Gmail OAuth
        display.text(display.width // 2, display.height - 30,
                    'Press G for Gmail (OAuth)', '#4285f4', 10, 'mm')
        display.text(display.width // 2, display.height - 15,
                    'or use App Password', '#666666', 9, 'mm')
    
    def _draw_gmail_auth(self, display: Display):
        """Draw Gmail OAuth authentication screen."""
        center_y = display.height // 2
        
        # Title
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 25,
                    "Gmail Login", 'white', 16, 'mm')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 45,
                    "Device Flow OAuth", '#888888', 10, 'mm')
        
        if self.gmail_user_code:
            # Show the code
            display.text(display.width // 2, center_y - 45,
                        "On your phone/computer,", '#888888', 11, 'mm')
            display.text(display.width // 2, center_y - 30,
                        "go to:", '#888888', 11, 'mm')
            display.text(display.width // 2, center_y - 10,
                        self.gmail_verification_url, '#4285f4', 12, 'mm')
            
            display.text(display.width // 2, center_y + 15,
                        "Enter this code:", '#888888', 11, 'mm')
            
            # Big code display
            display.rect(35, center_y + 30, display.width - 70, 45, 
                        fill='#1a1a2e', outline='#4285f4')
            display.text(display.width // 2, center_y + 52,
                        self.gmail_user_code, '#ffffff', 22, 'mm')
            
            display.text(display.width // 2, center_y + 90,
                        "Waiting for you...", '#888888', 10, 'mm')
        else:
            display.text(display.width // 2, center_y,
                        self.gmail_auth_status or "Starting...", '#888888', 12, 'mm')
        
        display.text(display.width // 2, display.height - 15,
                    "ESC to cancel", '#666666', 10, 'mm')


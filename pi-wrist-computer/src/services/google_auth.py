"""
Google Device Flow Authentication
For headless devices without browser access.

Flow:
1. Request device code from Google
2. Display code to user
3. User visits google.com/device on another device
4. User enters code
5. App polls for token completion
6. Token is saved for future use
"""

import os
import json
import time
import pickle
import threading
from typing import Optional, Callable, List, Dict
import requests


class GoogleDeviceAuth:
    """
    Google OAuth using Device Flow.
    
    Works without a browser - shows a code for user to enter
    on another device (phone/computer).
    """
    
    DEVICE_AUTH_URL = "https://oauth2.googleapis.com/device/code"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    
    # Default scopes
    SCOPES = {
        'calendar': [
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events',
        ],
        'gmail': [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.modify',
        ],
        'drive': [
            'https://www.googleapis.com/auth/drive.readonly',
        ],
    }
    
    def __init__(self, 
                 client_id: str,
                 client_secret: str,
                 scopes: List[str],
                 token_path: str = None,
                 on_code_received: Callable[[str, str], None] = None,
                 on_auth_complete: Callable[[dict], None] = None,
                 on_auth_error: Callable[[str], None] = None):
        """
        Initialize Google Device Auth.
        
        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            scopes: List of OAuth scopes
            token_path: Path to save token (default: ~/.google_token.pickle)
            on_code_received: Callback(user_code, verification_url) when code ready
            on_auth_complete: Callback(token_data) when auth completes
            on_auth_error: Callback(error_message) on error
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.token_path = token_path or os.path.expanduser("~/.google_token.pickle")
        
        self.on_code_received = on_code_received
        self.on_auth_complete = on_auth_complete
        self.on_auth_error = on_auth_error
        
        self.token_data: Optional[dict] = None
        self.device_code: Optional[str] = None
        self.user_code: Optional[str] = None
        self.verification_url: Optional[str] = None
        self.poll_interval: int = 5
        self.expires_in: int = 0
        
        self.polling = False
        self._poll_thread: Optional[threading.Thread] = None
        
        # Try to load existing token
        self._load_token()
    
    def _load_token(self) -> bool:
        """Load saved token if exists."""
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as f:
                    self.token_data = pickle.load(f)
                return True
            except Exception as e:
                print(f"Error loading token: {e}")
        return False
    
    def _save_token(self):
        """Save token to disk."""
        if self.token_data:
            try:
                with open(self.token_path, 'wb') as f:
                    pickle.dump(self.token_data, f)
            except Exception as e:
                print(f"Error saving token: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if we have a valid token."""
        if not self.token_data:
            return False
        
        # Check if expired
        if 'expires_at' in self.token_data:
            if time.time() >= self.token_data['expires_at']:
                # Try to refresh
                return self.refresh_token()
        
        return 'access_token' in self.token_data
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token, refreshing if needed."""
        if not self.is_authenticated():
            return None
        return self.token_data.get('access_token')
    
    def start_auth(self) -> bool:
        """
        Start the device authentication flow.
        
        Returns True if device code was obtained successfully.
        """
        try:
            response = requests.post(self.DEVICE_AUTH_URL, data={
                'client_id': self.client_id,
                'scope': ' '.join(self.scopes),
            })
            
            if response.status_code != 200:
                error = response.json().get('error_description', 'Unknown error')
                if self.on_auth_error:
                    self.on_auth_error(error)
                return False
            
            data = response.json()
            
            self.device_code = data['device_code']
            self.user_code = data['user_code']
            self.verification_url = data.get('verification_url', 'https://google.com/device')
            self.poll_interval = data.get('interval', 5)
            self.expires_in = data.get('expires_in', 1800)
            
            if self.on_code_received:
                self.on_code_received(self.user_code, self.verification_url)
            
            # Start polling for token
            self._start_polling()
            
            return True
            
        except Exception as e:
            if self.on_auth_error:
                self.on_auth_error(str(e))
            return False
    
    def _start_polling(self):
        """Start polling for token in background."""
        self.polling = True
        self._poll_thread = threading.Thread(target=self._poll_for_token, daemon=True)
        self._poll_thread.start()
    
    def _poll_for_token(self):
        """Poll Google for token (runs in background thread)."""
        start_time = time.time()
        
        while self.polling and (time.time() - start_time) < self.expires_in:
            time.sleep(self.poll_interval)
            
            try:
                response = requests.post(self.TOKEN_URL, data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'device_code': self.device_code,
                    'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                })
                
                data = response.json()
                
                if 'access_token' in data:
                    # Success!
                    self.token_data = data
                    self.token_data['expires_at'] = time.time() + data.get('expires_in', 3600)
                    self._save_token()
                    self.polling = False
                    
                    if self.on_auth_complete:
                        self.on_auth_complete(data)
                    return
                
                error = data.get('error', '')
                
                if error == 'authorization_pending':
                    # User hasn't entered code yet, keep polling
                    continue
                elif error == 'slow_down':
                    # Increase poll interval
                    self.poll_interval += 5
                elif error == 'access_denied':
                    self.polling = False
                    if self.on_auth_error:
                        self.on_auth_error("Access denied by user")
                    return
                elif error == 'expired_token':
                    self.polling = False
                    if self.on_auth_error:
                        self.on_auth_error("Code expired")
                    return
                    
            except Exception as e:
                print(f"Poll error: {e}")
                continue
        
        self.polling = False
        if self.on_auth_error:
            self.on_auth_error("Authentication timed out")
    
    def refresh_token(self) -> bool:
        """Refresh the access token using refresh token."""
        if not self.token_data or 'refresh_token' not in self.token_data:
            return False
        
        try:
            response = requests.post(self.TOKEN_URL, data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.token_data['refresh_token'],
                'grant_type': 'refresh_token',
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token_data['access_token'] = data['access_token']
                self.token_data['expires_at'] = time.time() + data.get('expires_in', 3600)
                self._save_token()
                return True
            
        except Exception as e:
            print(f"Refresh error: {e}")
        
        return False
    
    def cancel_auth(self):
        """Cancel ongoing authentication."""
        self.polling = False
    
    def logout(self):
        """Clear saved token."""
        self.token_data = None
        if os.path.exists(self.token_path):
            os.remove(self.token_path)


class GoogleCredentials:
    """
    Helper to load Google OAuth credentials from file.
    
    Credentials file format (JSON):
    {
        "client_id": "your-client-id.apps.googleusercontent.com",
        "client_secret": "your-client-secret"
    }
    
    Or use the downloaded credentials from Google Cloud Console.
    """
    
    def __init__(self, credentials_path: str = None):
        self.path = credentials_path or os.path.expanduser("~/google_credentials.json")
        self.client_id = None
        self.client_secret = None
        self._load()
    
    def _load(self):
        """Load credentials from file."""
        if not os.path.exists(self.path):
            return
        
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
            
            # Handle both direct format and Google Console download format
            if 'installed' in data:
                data = data['installed']
            elif 'web' in data:
                data = data['web']
            
            self.client_id = data.get('client_id')
            self.client_secret = data.get('client_secret')
            
        except Exception as e:
            print(f"Error loading credentials: {e}")
    
    def is_valid(self) -> bool:
        """Check if credentials are loaded."""
        return self.client_id is not None and self.client_secret is not None
    
    def create_auth(self, scopes: List[str], token_path: str = None, **kwargs) -> GoogleDeviceAuth:
        """
        Create a GoogleDeviceAuth instance with these credentials.
        
        Args:
            scopes: List of OAuth scopes
            token_path: Path to save token
            **kwargs: Additional args for GoogleDeviceAuth
        """
        return GoogleDeviceAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=scopes,
            token_path=token_path,
            **kwargs
        )


# Convenience functions for specific services

def create_calendar_auth(credentials_path: str = None, 
                         token_path: str = None,
                         **kwargs) -> Optional[GoogleDeviceAuth]:
    """Create auth for Google Calendar."""
    creds = GoogleCredentials(credentials_path)
    if not creds.is_valid():
        return None
    
    return creds.create_auth(
        scopes=GoogleDeviceAuth.SCOPES['calendar'],
        token_path=token_path or os.path.expanduser("~/.google_calendar_token.pickle"),
        **kwargs
    )


def create_gmail_auth(credentials_path: str = None,
                      token_path: str = None,
                      **kwargs) -> Optional[GoogleDeviceAuth]:
    """Create auth for Gmail."""
    creds = GoogleCredentials(credentials_path)
    if not creds.is_valid():
        return None
    
    return creds.create_auth(
        scopes=GoogleDeviceAuth.SCOPES['gmail'],
        token_path=token_path or os.path.expanduser("~/.google_gmail_token.pickle"),
        **kwargs
    )


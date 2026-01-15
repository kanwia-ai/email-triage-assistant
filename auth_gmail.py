"""One-time Gmail authorization script."""
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import json

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

print("Opening browser for Gmail authorization...")
print("Please sign in and grant access to your Gmail.")

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=8080)

# Save the token
with open('token.json', 'w') as token:
    token.write(creds.to_json())

print("\nAuthorization successful!")
print("Token saved to token.json")

# Also output the token JSON for Cloud Run env var
print("\n--- GMAIL_TOKEN_JSON (for Cloud Run) ---")
print(creds.to_json())

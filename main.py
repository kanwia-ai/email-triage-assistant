"""
Email Triage Assistant

Daily email digest sent via Slack DM with intelligent classification.
Auto-archives obvious noise, surfaces everything else for review.
"""

import os
import json
import base64
from datetime import datetime, timedelta
from typing import Optional
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Configuration from environment variables
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_USER_ID = os.environ.get('SLACK_USER_ID')
USER_EMAIL = os.environ.get('USER_EMAIL', 'your-email@example.com')

# Classification prompt
CLASSIFICATION_PROMPT = """You are Kyra's email assistant at Section (an AI training company).

CONTEXT ABOUT KYRA'S ROLE:
- She works with external clients on AI training programs
- Her managers are Greg Shove (CEO) and Lauren Kaufman Witten
- Section uses Slack internally, so internal emails are rare and important
- She coordinates with external instructors/consultants for training delivery
- She approves invoices weekly via billing system emails

CLASSIFICATION RULES:

RESPOND (needs her action):
- Emails from Greg Shove or Lauren Kaufman Witten
- External client emails where she's directly addressed or asked a question
- Billing/approval requests requiring her sign-off
- Calendar invites requiring a response
- Any email with a direct question to her

FYI (keep visible, no action needed):
- Client threads where she's CC'd but not directly addressed
- Instructor/consultant coordination that's informational
- Internal Section emails (rare, so likely notable)

ARCHIVE (obvious noise - no action needed):
- Invoice/receipt submissions with no question attached
- Calendar notifications (not invites that need RSVP)
- Zoom, Google Meet, or other meeting tool notifications (recordings ready, meeting assets, transcripts)
- "Meeting assets ready" / "Meeting summary ready" / "Meeting pre-read" notifications
- Automated confirmations (DocuSign completed, etc.)
- System notifications, newsletters, marketing
- Payment sent/received notifications
- "Accepted" / "Declined" calendar responses from others
- Task reminder digests
- Automated meeting summaries from AI tools (Otter, Fireflies, etc.)

CRITICAL: Read the full email body. An invoice submission WITH a question = RESPOND. Context matters more than sender.

EMAIL TO CLASSIFY:
From: {sender}
Subject: {subject}
Body snippet: {body}

Return ONLY valid JSON:
{{"tier": "RESPOND" | "FYI" | "ARCHIVE", "confidence": "high" | "medium" | "low", "reason": "brief explanation", "summary": "one line description"}}"""


def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None
    token_path = '/tmp/gmail_token.json'
    creds_path = os.environ.get('GOOGLE_CREDENTIALS_PATH', 'credentials.json')

    # Check for credentials in environment variable (for Cloud Run)
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        creds_path = '/tmp/credentials.json'
        with open(creds_path, 'w') as f:
            f.write(creds_json)

    # Check for existing token in environment (for Cloud Run)
    token_json = os.environ.get('GMAIL_TOKEN_JSON')
    if token_json:
        with open(token_path, 'w') as f:
            f.write(token_json)

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def get_recent_emails(service, hours: int = 24) -> list:
    """Fetch unread emails from the last N hours."""
    emails = []

    # Calculate time threshold
    after_date = datetime.now() - timedelta(hours=hours)
    after_timestamp = int(after_date.timestamp())

    # Search for unread emails
    query = f'is:unread after:{after_timestamp}'

    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=50
        ).execute()

        messages = results.get('messages', [])

        for msg in messages:
            email_data = get_email_details(service, msg['id'])
            if email_data:
                emails.append(email_data)

        return emails

    except HttpError as error:
        print(f'Gmail API error: {error}')
        return []


def get_email_details(service, message_id: str) -> Optional[dict]:
    """Get details for a single email."""
    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        headers = message['payload']['headers']

        # Extract headers
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')

        # Extract body
        body = extract_body(message['payload'])

        # Build Gmail link
        gmail_link = f"https://mail.google.com/mail/u/0/#inbox/{message_id}"

        return {
            'id': message_id,
            'sender': sender,
            'subject': subject,
            'body': body[:1000],  # Limit for API
            'date': date_str,
            'gmail_link': gmail_link,
            'labels': message.get('labelIds', [])
        }

    except HttpError as error:
        print(f'Error getting email {message_id}: {error}')
        return None


def extract_body(payload: dict) -> str:
    """Extract plain text body from email payload."""
    body = ''

    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

    elif 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                break
            elif 'parts' in part:
                body = extract_body(part)
                if body:
                    break

    # Clean up the body
    body = body.replace('\r\n', '\n').strip()
    return body


def classify_email(email: dict) -> dict:
    """Classify email using Gemini API."""
    if not GEMINI_API_KEY:
        return {
            'tier': 'FYI',
            'confidence': 'low',
            'reason': 'No API key configured',
            'summary': email['subject'][:50]
        }

    prompt = CLASSIFICATION_PROMPT.format(
        sender=email['sender'],
        subject=email['subject'],
        body=email['body'][:800]
    )

    try:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'

        payload = {
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {
                'temperature': 0.1,
                'maxOutputTokens': 1024
            }
        }

        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        text = result['candidates'][0]['content']['parts'][0]['text']

        # Parse JSON from response - handle various formats
        import re

        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        # Try to extract individual fields with regex as fallback
        tier_match = re.search(r'"tier"\s*:\s*"(RESPOND|FYI|ARCHIVE)"', text, re.IGNORECASE)
        conf_match = re.search(r'"confidence"\s*:\s*"(high|medium|low)"', text, re.IGNORECASE)
        reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', text)
        summary_match = re.search(r'"summary"\s*:\s*"([^"]*)"', text)

        # Try JSON parse first, fall back to regex extraction
        try:
            json_match = re.search(r'\{[^{}]*\}', text)
            if json_match:
                classification = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found")
        except:
            # Build from regex matches
            classification = {
                'tier': tier_match.group(1) if tier_match else 'FYI',
                'confidence': conf_match.group(1) if conf_match else 'low',
                'reason': reason_match.group(1) if reason_match else 'Extracted from response',
                'summary': summary_match.group(1) if summary_match else email['subject'][:50]
            }

        return {
            'tier': classification.get('tier', 'FYI').upper(),
            'confidence': classification.get('confidence', 'medium').lower(),
            'reason': classification.get('reason', ''),
            'summary': classification.get('summary', email['subject'][:50])
        }

    except Exception as e:
        print(f'Gemini API error for "{email["subject"]}": {e}')
        return {
            'tier': 'FYI',
            'confidence': 'low',
            'reason': f'Classification error: {str(e)[:50]}',
            'summary': email['subject'][:50]
        }


def archive_email(service, message_id: str) -> bool:
    """Archive an email by removing INBOX label."""
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['INBOX', 'UNREAD']}
        ).execute()
        return True
    except HttpError as error:
        print(f'Error archiving {message_id}: {error}')
        return False


def send_slack_dm(message: str) -> bool:
    """Send a direct message via Slack."""
    if not SLACK_BOT_TOKEN or not SLACK_USER_ID:
        print('Slack not configured, printing to console:')
        print(message)
        return False

    try:
        # Open a DM channel
        response = requests.post(
            'https://slack.com/api/conversations.open',
            headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'},
            json={'users': SLACK_USER_ID}
        )
        response.raise_for_status()
        channel_id = response.json()['channel']['id']

        # Send message
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': f'Bearer {SLACK_BOT_TOKEN}'},
            json={
                'channel': channel_id,
                'text': message,
                'mrkdwn': True
            }
        )
        response.raise_for_status()
        return response.json().get('ok', False)

    except Exception as e:
        print(f'Slack error: {e}')
        return False


def format_slack_message(respond: list, fyi: list, archived: list) -> str:
    """Format the email digest as a Slack message."""
    today = datetime.now().strftime('%b %d')
    total = len(respond) + len(fyi) + len(archived)

    lines = [
        f"*Your Daily Email Digest - {today}*",
        f"_{total} emails processed_",
        ""
    ]

    # RESPOND tier
    lines.append("*RESPOND* ({})".format(len(respond)))
    if respond:
        for item in respond:
            sender_name = item['email']['sender'].split('<')[0].strip()
            lines.append(f"  *{sender_name}* - \"{item['email']['subject'][:40]}\"")
            lines.append(f"    _{item['classification']['summary']}_")
            lines.append(f"    <{item['email']['gmail_link']}|Open in Gmail>")
    else:
        lines.append("  _None_")
    lines.append("")

    # FYI tier
    lines.append("*FYI / CC'd* ({})".format(len(fyi)))
    if fyi:
        for item in fyi[:10]:  # Limit to 10
            sender_name = item['email']['sender'].split('<')[0].strip()
            lines.append(f"  {sender_name} - \"{item['email']['subject'][:40]}\"")
            lines.append(f"    _{item['classification']['reason'][:60]}_")
            lines.append(f"    <{item['email']['gmail_link']}|Open>")
        if len(fyi) > 10:
            lines.append(f"  _...and {len(fyi) - 10} more_")
    else:
        lines.append("  _None_")
    lines.append("")

    # ARCHIVED tier
    lines.append("*AUTO-ARCHIVED* ({})".format(len(archived)))
    if archived:
        # Group by reason
        reasons = {}
        for item in archived:
            reason = item['classification']['reason'][:30]
            if reason not in reasons:
                reasons[reason] = 0
            reasons[reason] += 1

        for reason, count in list(reasons.items())[:5]:
            lines.append(f"  {count}x - {reason}")
    else:
        lines.append("  _None_")

    return '\n'.join(lines)


def main():
    """Main entry point."""
    print(f"Starting email triage at {datetime.now()}")

    # Initialize Gmail service
    service = get_gmail_service()

    # Fetch recent emails
    print("Fetching unread emails from last 24 hours...")
    emails = get_recent_emails(service, hours=24)
    print(f"Found {len(emails)} unread emails")

    if not emails:
        message = f"*Your Daily Email Digest - {datetime.now().strftime('%b %d')}*\n\n_No unread emails from the last 24 hours. Inbox zero!_"
        send_slack_dm(message)
        return

    # Classify each email
    respond_emails = []
    fyi_emails = []
    archived_emails = []

    import time
    for email in emails:
        print(f"Classifying: {email['subject'][:50]}...")
        classification = classify_email(email)
        time.sleep(2)  # Rate limiting - avoid 429 errors

        result = {
            'email': email,
            'classification': classification
        }

        tier = classification['tier']
        confidence = classification['confidence']

        if tier == 'RESPOND':
            respond_emails.append(result)
        elif tier == 'ARCHIVE' and confidence == 'high':
            # Auto-archive high-confidence noise
            if archive_email(service, email['id']):
                archived_emails.append(result)
            else:
                fyi_emails.append(result)
        else:
            # FYI tier, or low-confidence ARCHIVE
            fyi_emails.append(result)

    # Send Slack digest
    message = format_slack_message(respond_emails, fyi_emails, archived_emails)
    send_slack_dm(message)

    print(f"Done! RESPOND: {len(respond_emails)}, FYI: {len(fyi_emails)}, ARCHIVED: {len(archived_emails)}")


# Cloud Run entry point
def handler(request):
    """HTTP handler for Cloud Run."""
    main()
    return 'OK', 200


if __name__ == '__main__':
    main()

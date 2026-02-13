# Email Triage Assistant

AI-powered daily email digest that classifies your inbox and delivers a prioritized summary via Slack DM.

## What It Does

The assistant connects to your Gmail account, reads unread emails from the last 24 hours, classifies each one using Gemini, auto-archives obvious noise, and sends you a structured Slack digest with everything that matters.

## Features

- **Three-tier classification** -- emails are sorted into RESPOND (needs your action), FYI (informational), and ARCHIVE (noise)
- **Auto-archiving** -- high-confidence noise (meeting notifications, payment receipts, automated summaries) is archived without manual intervention
- **Slack DM digest** -- a single daily message groups emails by priority with direct Gmail links
- **Context-aware rules** -- classification prompt is tuned for a specific role and workflow, not generic heuristics
- **Runs on a schedule** -- deployed to Google Cloud Run and triggered by Cloud Scheduler

## Tech Stack

- Python 3.11
- Gmail API (read and modify)
- Google Gemini 2.0 Flash (classification)
- Slack API (DM delivery)
- Flask (Cloud Run entry point)
- Google Cloud Run + Cloud Build (deployment)
- Cloud Scheduler (daily trigger)

## Setup

### Prerequisites

- Google Cloud project with Gmail API, Cloud Run, Cloud Scheduler, and Cloud Build enabled
- OAuth 2.0 credentials for Gmail (desktop app type)
- Slack bot token with chat:write and im:write scopes
- Gemini API key

### Environment Variables

| Variable | Description |
|----------|-------------|
| GEMINI_API_KEY | Google Gemini API key |
| SLACK_BOT_TOKEN | Slack bot OAuth token |
| SLACK_USER_ID | Your Slack member ID |
| USER_EMAIL | Your Gmail address |
| GOOGLE_CREDENTIALS_JSON | OAuth client credentials JSON (for Cloud Run) |
| GMAIL_TOKEN_JSON | Gmail auth token JSON (for Cloud Run) |

### Local Development

1. Clone the repo and install dependencies:

       pip install -r requirements.txt

2. Place your OAuth credentials file as credentials.json in the project root.

3. Run the one-time Gmail authorization:

       python auth_gmail.py

4. Set environment variables and run:

       python main.py

### Deployment

The included cloudbuild.yaml and Dockerfile handle deployment to Cloud Run. Secrets are managed through Google Secret Manager. See BROWSER_SETUP_INSTRUCTIONS.md for a step-by-step guide to configuring Slack, Google Cloud, and Gemini credentials.

## Project Structure

    app.py          Flask entry point for Cloud Run
    main.py         Core logic: fetch, classify, archive, notify
    auth_gmail.py   One-time Gmail OAuth authorization
    cloudbuild.yaml Cloud Build deployment config
    Dockerfile      Container definition

## License

See LICENSE for details.

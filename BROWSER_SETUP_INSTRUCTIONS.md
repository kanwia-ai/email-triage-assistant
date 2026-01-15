# Browser Setup Instructions for Claude Browser Agent

These instructions need to be done in a web browser. Give these to your Claude browser agent.

---

## Part 1: Create Slack App (10 minutes)

### Step 1: Go to Slack API
1. Navigate to https://api.slack.com/apps
2. Click "Create New App"
3. Choose "From scratch"
4. App Name: "Email Triage Assistant"
5. Workspace: Select your Section workspace
6. Click "Create App"

### Step 2: Configure Bot Permissions
1. In the left sidebar, click "OAuth & Permissions"
2. Scroll to "Scopes" section
3. Under "Bot Token Scopes", click "Add an OAuth Scope"
4. Add these scopes:
   - `chat:write` (send messages)
   - `im:write` (send DMs)
5. Scroll up and click "Install to Workspace"
6. Click "Allow"

### Step 3: Get Your Credentials
1. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
   - **Save this as: SLACK_BOT_TOKEN**
2. Go to your Slack workspace
3. Click on your profile picture → "Profile"
4. Click the "..." menu → "Copy member ID"
   - **Save this as: SLACK_USER_ID**

---

## Part 2: Create Google Cloud Project (15 minutes)

### Step 1: Create Project
1. Go to https://console.cloud.google.com
2. Click the project dropdown at the top
3. Click "New Project"
4. Project name: "email-triage-assistant"
5. Click "Create"
6. Wait for creation, then select the new project

### Step 2: Enable APIs
1. Go to https://console.cloud.google.com/apis/library
2. Search for "Gmail API" → Click it → Click "Enable"
3. Search for "Cloud Run Admin API" → Click it → Click "Enable"
4. Search for "Cloud Scheduler API" → Click it → Click "Enable"
5. Search for "Cloud Build API" → Click it → Click "Enable"

### Step 3: Create OAuth Credentials
1. Go to https://console.cloud.google.com/apis/credentials
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure consent screen first:
   - User Type: "Internal" (if available) or "External"
   - App name: "Email Triage Assistant"
   - User support email: your email
   - Developer contact: your email
   - Click "Save and Continue" through the rest
4. Back to Create Credentials → "OAuth client ID"
5. Application type: "Desktop app"
6. Name: "Email Triage CLI"
7. Click "Create"
8. Click "Download JSON"
9. **Save the downloaded file as `credentials.json`**

### Step 4: Get Project ID
1. Click the project dropdown at the top
2. Note your project ID (looks like "email-triage-assistant" or "email-triage-assistant-xxxxx")
   - **Save this as: PROJECT_ID**

---

## Part 3: Get Gemini API Key (2 minutes)

1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API key"
3. Select the project you just created
4. Click "Create API key in existing project"
5. Copy the API key
   - **Save this as: GEMINI_API_KEY**

---

## Summary: Values to Save

After completing these steps, you should have:

| Variable | Value |
|----------|-------|
| SLACK_BOT_TOKEN | xoxb-... |
| SLACK_USER_ID | U... |
| PROJECT_ID | email-triage-assistant-... |
| GEMINI_API_KEY | AI... |
| credentials.json | Downloaded file |

Give these back to the terminal Claude to continue deployment.

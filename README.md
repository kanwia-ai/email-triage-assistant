# Email Triage Assistant

AI-powered daily email digest that classifies your inbox and delivers a prioritized summary via Slack DM.

## What It Does

The assistant connects to your Gmail account, reads unread emails from the last 24 hours, classifies each one using Gemini, auto-archives obvious noise, and sends you a structured Slack digest with everything that matters.

## Features

- **Three-tier classification** -- emails are sorted into RESPOND (needs your action), FYI (informational), and ARCHIVE (noise)
- **Auto-archiving** -- high-confidence noise (meeting notifications, payment receipts, automated summaries) is archived without manual intervention
- **Slack DM digest** -- a single daily message groups emails by priority with direct Gmail links
- |*Context-aware rules** -- classification prompt is tuned for a specific role and workflow, not generic heuristics
- |*Runs on a schedule** -- deployed to Google Cloud Run and triggered by Cloud Scheduler

# Setup Guide

This guide details exactly how to hook up external dependency pipelines to VyapaarClaw. Namely: Slack Human-in-the-Loop integration, and secure tunneling (via ngrok) for local development webhook receipt.

---

## 1. Local Webhook Tunnel Setup (ngrok)

To receive webhooks locally from Razorpay in development, you need an ingress proxy.

1. Install ngrok via Homebrew (macOS): `brew install ngrok/ngrok/ngrok`
2. Obtain your `NGROK_AUTHTOKEN` from the ngrok dashboard.
3. Add it to your `.env` securely. Never run `ngrok config add-authtoken <token>` directly in bash to prevent shell history leaks.
4. Run the tunnel via environmental variables:
   ```bash
   ngrok http 8000 --authtoken $NGROK_AUTHTOKEN
   ```
5. Configure the RazorpayX portal settings:
   - Go to **Settings > Webhooks** in your RazorpayX dashboard.
   - Point it to your generated tunnel URL plus the webhook path (`https://<your-id>.ngrok-free.app/webhook/razorpay`).
   - Copy the Razorpay webhook signing secret and place it in your `.env` as `VYAPAAR_RAZORPAY_WEBHOOK_SECRET`.

---

## 2. Slack Application Registration

Slack is responsible for pinging operations members to manually verify high-value flagged payouts.

1. Navigate to the [Slack API: Your Apps](https://api.slack.com/apps) dashboard.
2. Click **Create New App** -> **From Scratch**. 
3. Name it **VyapaarClaw** and attach it to your target workspace workspace.
4. Open the **OAuth & Permissions** menu on the left sidebar.
5. Under **Bot Token Scopes**, add the following permissions:
   - `chat:write`
   - `chat:write.public`
6. Click **Install to Workspace**. Save the resulting `xoxb-` token to your `.env` as `SLACK_BOT_TOKEN`.

### Resolving Channel routing
- Create a channel (e.g., `#vyapaar-alerts`).
- Right-click the channel, select **View channel details**, and copy the **Channel ID** (starts with C, e.g., `C01GHJKLMN`). Attach this to `.env` as `SLACK_CHANNEL_ID`.
- In Slack web-browser mode, check the URL payload (e.g. `client/T01ABCDEFGH/...`). Extract the text block starting with `T` as the workspace id. Attach this to `.env` as `SLACK_TEAM_ID`.

Finally, securely invite the bot into your channel by typing `/invite @VyapaarClaw`.

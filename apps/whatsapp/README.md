# SATARK WhatsApp Bridge

This service connects WhatsApp messages to the existing SATARK channel pipeline.
Survey generation is not changed. The bridge only forwards citizen messages to:

```text
POST /api/v1/channels/whatsapp/webhook
```

The backend then starts the latest published survey, asks one question at a time,
runs the normal validation/trust pipeline, and persists the final response.

## Run Locally

1. Start the SATARK backend.
2. Install dependencies once:

```bash
npm install
```

3. Start the bridge:

```bash
npm run dev
```

4. Scan the terminal QR code from WhatsApp > Linked devices.
5. Send `Hi` to the linked WhatsApp account.

The bot replies as SATARK, asks for consent, then sends the survey questions one by one.

## Configuration

Use `apps/whatsapp/.env`:

```text
BACKEND_URL=http://127.0.0.1:8001
BOT_NAME=SATARK
SURVEY_ID=
DEFAULT_LANGUAGE=en
REQUEST_TIMEOUT_MS=15000
```

Leave `SURVEY_ID` blank to use the latest published survey. Set it only when you
want WhatsApp to collect a specific survey id.

## Security Notes

`auth_info_baileys/` stores WhatsApp linked-device credentials. It must stay out
of git and should be treated like a secret.

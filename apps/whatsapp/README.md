# SATARK WhatsApp Bridge

This service connects WhatsApp messages to the existing SATARK channel pipeline.
Survey generation is not changed. The bridge only forwards citizen messages to:

```text
POST /api/v1/channels/whatsapp/webhook
```

The backend then starts the latest published survey, asks one question at a time,
runs the normal validation/trust pipeline, and persists the final response.

## Run Against The Deployed SATARK Backend

This is the recommended path for a teammate who only needs the WhatsApp bot.
The bot runs on their laptop, but surveys/responses come from the deployed
SATARK backend and database.

```powershell
git clone https://github.com/joeldeva/SATARK.git
cd SATARK\apps\whatsapp
.\setup-deployed-env.ps1
npm install
npm run dev
```

Then scan the terminal QR code from WhatsApp > Linked devices. From another
WhatsApp number, send `Hi` to the linked WhatsApp account.

With the default `.env`, `SURVEY_ID` is blank, so the backend selects the latest
published survey from `https://satark-api.onrender.com`.

## Run With A Local SATARK Backend

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
BACKEND_URL=https://satark-api.onrender.com
BOT_NAME=SATARK
SURVEY_ID=
DEFAULT_LANGUAGE=en
REQUEST_TIMEOUT_MS=30000
BAILEYS_AUTH_DIR=auth_info_deployed
```

Leave `SURVEY_ID` blank to use the latest published survey. Set it only when you
want WhatsApp to collect a specific survey id.

## Security Notes

`auth_info_baileys/` stores WhatsApp linked-device credentials. It must stay out
of git and should be treated like a secret.

`auth_info_deployed/` is also ignored for the same reason.

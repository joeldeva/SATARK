import makeWASocket, {
  DisconnectReason,
  fetchLatestWaWebVersion,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';
import axios from 'axios';
import dotenv from 'dotenv';
import path from 'path';
import pino from 'pino';
import QRCode from 'qrcode';
import qrcode from 'qrcode-terminal';
import { fileURLToPath } from 'url';

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BACKEND_URL = (process.env.BACKEND_URL || 'http://127.0.0.1:8001').replace(/\/$/, '');
const BOT_NAME = process.env.BOT_NAME || 'SATARK';
const SURVEY_ID = (process.env.SURVEY_ID || '').trim();
const DEFAULT_LANGUAGE = process.env.DEFAULT_LANGUAGE || 'en';
const AUTH_DIR = process.env.BAILEYS_AUTH_DIR || path.join(__dirname, 'auth_info_baileys');
const QR_IMAGE_PATH = process.env.QR_IMAGE_PATH || path.join(__dirname, 'logs', 'whatsapp-qr.png');
const REQUEST_TIMEOUT_MS = Number(process.env.REQUEST_TIMEOUT_MS || 15000);

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const welcomedSenders = new Set();

function extractText(message) {
  const content = message?.message || {};
  return (
    content.conversation ||
    content.extendedTextMessage?.text ||
    content.imageMessage?.caption ||
    content.videoMessage?.caption ||
    content.documentMessage?.caption ||
    content.buttonsResponseMessage?.selectedButtonId ||
    content.templateButtonReplyMessage?.selectedId ||
    content.listResponseMessage?.singleSelectReply?.selectedRowId ||
    ''
  ).trim();
}

function isGreeting(text) {
  return ['hi', 'hello', 'start', 'satark', 'survey'].includes(String(text).trim().toLowerCase());
}

function isRestart(text) {
  return ['restart', 'reset', 'start over', '/restart'].includes(String(text).trim().toLowerCase());
}

function plainNumber(jid) {
  return String(jid || '').replace(/@s\.whatsapp\.net$/, '').replace(/@g\.us$/, '');
}

function buildWebhookBody(sender, text, reset = false) {
  const body = {
    sender,
    from: plainNumber(sender),
    text,
    language: DEFAULT_LANGUAGE,
    channel: 'whatsapp',
    reset,
  };
  if (SURVEY_ID) body.survey_id = SURVEY_ID;
  return body;
}

function localIntro() {
  return `Hi, I'm ${BOT_NAME}, the official survey assistant. Please fill this survey. I will ask one question at a time.`;
}

function formatOptions(options = []) {
  if (!Array.isArray(options) || options.length === 0) return '';
  return options
    .map((option, index) => {
      const label = option?.label_i18n?.[DEFAULT_LANGUAGE] || option?.label_i18n?.en || option?.label || option?.value;
      return `${index + 1}. ${label}`;
    })
    .join('\n');
}

function formatOutbound(payload, backendReply, prependIntro = false) {
  const prompt = payload?.prompt_text?.[DEFAULT_LANGUAGE] || payload?.prompt_text?.en || backendReply || '';
  const options = formatOptions(payload?.options);
  const type = payload?.type;
  const pieces = [];

  if (prependIntro) pieces.push(localIntro());
  if (prompt) pieces.push(prompt);
  if (options && type !== 'complete') {
    pieces.push(`Reply with the option number or the answer text:\n${options}`);
  }
  if (type === 'complete') {
    pieces.push(`Thank you for completing the survey with ${BOT_NAME}.`);
  }

  return pieces.join('\n\n').trim();
}

async function sendToBackend(sender, text, reset = false) {
  const response = await axios.post(
    `${BACKEND_URL}/api/v1/channels/whatsapp/webhook`,
    buildWebhookBody(sender, text, reset),
    {
      timeout: REQUEST_TIMEOUT_MS,
      headers: { 'Content-Type': 'application/json' },
    },
  );
  return response.data;
}

async function assertBackendReady() {
  try {
    const response = await axios.get(`${BACKEND_URL}/health/ready`, { timeout: REQUEST_TIMEOUT_MS });
    if (!response.data?.ready) {
      logger.warn({ backend: BACKEND_URL, readiness: response.data }, 'SATARK backend is reachable but not fully ready');
    } else {
      logger.info({ backend: BACKEND_URL }, 'SATARK backend readiness check passed');
    }
  } catch (error) {
    const details = error.response?.data || error.message;
    logger.warn({ backend: BACKEND_URL, details }, 'SATARK backend readiness check failed; WhatsApp will still start and retry per message');
  }
}

async function handleInbound(sock, sender, text) {
  const firstContact = !welcomedSenders.has(sender) && isGreeting(text);
  const restart = isRestart(text);
  const normalizedText = firstContact || restart ? 'hi' : text;

  const data = await sendToBackend(sender, normalizedText, restart);
  const reply = formatOutbound(data.payload, data.reply || data.reply_text, firstContact || restart);

  welcomedSenders.add(sender);
  if (reply) {
    logger.info({ sender, type: data.payload?.type, node: data.payload?.node_id }, 'sending WhatsApp survey prompt');
    await sock.sendMessage(sender, { text: reply });
  }
}

async function connectToWhatsApp() {
  await assertBackendReady();
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version, isLatest } = await fetchLatestWaWebVersion().catch(() => ({
    version: [2, 3000, 1017577713],
    isLatest: false,
  }));

  logger.info(
    {
      backend: BACKEND_URL,
      survey: SURVEY_ID || 'latest published',
      version: version.join('.'),
      isLatest,
    },
    `${BOT_NAME} WhatsApp bridge starting`,
  );

  const socketFactory = makeWASocket.default || makeWASocket;
  const sock = socketFactory({
    version,
    auth: state,
    logger: pino({ level: process.env.BAILEYS_LOG_LEVEL || 'silent' }),
    printQRInTerminal: false,
  });

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      await QRCode.toFile(QR_IMAGE_PATH, qr, { width: 640, margin: 2 });
      console.log('\n--- SCAN THIS QR CODE WITH WHATSAPP LINKED DEVICES ---');
      console.log(`QR image: ${QR_IMAGE_PATH}`);
      qrcode.generate(qr, { small: true });
      console.log('------------------------------------------------------\n');
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      logger.warn({ statusCode, shouldReconnect }, 'WhatsApp connection closed');
      if (shouldReconnect) connectToWhatsApp();
    }

    if (connection === 'open') {
      logger.info(`${BOT_NAME} WhatsApp bridge connected`);
    }
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('messages.upsert', async (event) => {
    if (event.type !== 'notify') return;

    for (const msg of event.messages || []) {
      if (msg.key.fromMe) continue;
      const sender = msg.key.remoteJid;
      const text = extractText(msg);
      if (!sender || !text) continue;

      logger.info({ sender, text }, 'received WhatsApp message');
      try {
        await handleInbound(sock, sender, text);
      } catch (error) {
        const details = error.response?.data || error.message;
        logger.error({ sender, details }, 'SATARK backend bridge failed');
        const status = error.response?.status ? ` Backend returned ${error.response.status}.` : '';
        await sock.sendMessage(sender, {
          text: `${BOT_NAME} cannot reach the survey server right now.${status} Please make sure the SATARK backend is running and try again.`,
        });
      }
    }
  });
}

connectToWhatsApp().catch((error) => {
  logger.error({ error }, 'Failed to run WhatsApp bot');
  process.exitCode = 1;
});

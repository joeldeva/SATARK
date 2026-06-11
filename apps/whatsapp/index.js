import makeWASocket, { useMultiFileAuthState, DisconnectReason, fetchLatestWaWebVersion } from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import axios from 'axios';
import dotenv from 'dotenv';
import pino from 'pino';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001';
const SECRET_KEY = process.env.SECRET_KEY || 'dev-secret-key-change-in-production';

const logger = pino({ level: 'info' });

async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(path.join(__dirname, 'auth_info_baileys'));

  const { version, isLatest } = await fetchLatestWaWebVersion().catch(() => ({
    version: [2, 3000, 1017577713], // fallback
    isLatest: false
  }));
  console.log(`Using WhatsApp Web version: ${version.join('.')}, isLatest: ${isLatest}`);

  const sock = (makeWASocket.default || makeWASocket)({
    version,
    auth: state,
    logger: pino({ level: 'silent' }) // suppress verbose websocket traces
  });

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('\n--- SCAN QR CODE WITH WHATSAPP TO LOG IN ---');
      qrcode.generate(qr, { small: true });
      console.log('--------------------------------------------\n');
    }

    if (connection === 'close') {
      const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log('WhatsApp connection closed due to:', lastDisconnect?.error, '. Reconnecting:', shouldReconnect);
      if (shouldReconnect) {
        connectToWhatsApp();
      }
    } else if (connection === 'open') {
      console.log('WhatsApp connection successfully opened!');
    }
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('messages.upsert', async (m) => {
    if (m.type !== 'notify') return;

    for (const msg of m.messages) {
      if (msg.key.fromMe) continue;

      const sender = msg.key.remoteJid;
      const messageText = (
        msg.message?.conversation ||
        msg.message?.extendedTextMessage?.text ||
        msg.message?.buttonsResponseMessage?.selectedButtonId ||
        msg.message?.templateButtonReplyMessage?.selectedId ||
        ''
      ).trim();

      if (!messageText) continue;

      console.log(`Received message from ${sender}: "${messageText}"`);

      try {
        const response = await axios.post(
          `${BACKEND_URL}/api/whatsapp/webhook`,
          {
            sender: sender,
            text: messageText
          },
          {
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${SECRET_KEY}`
            }
          }
        );

        const reply = response.data.reply;
        if (reply) {
          console.log(`Sending reply to ${sender}: "${reply.replace(/\n/g, ' ')}"`);
          await sock.sendMessage(sender, { text: reply });
        }
      } catch (error) {
        console.error('Error contacting SATARK backend:', error.message);
        if (error.response) {
          console.error('Backend error details:', error.response.data);
        }
        await sock.sendMessage(sender, {
          text: '⚠️ SATARK NSS Survey Assistant is currently experiencing connection issues. Please try again later.'
        });
      }
    }
  });
}

connectToWhatsApp().catch(err => console.error('Failed to run WhatsApp bot:', err));

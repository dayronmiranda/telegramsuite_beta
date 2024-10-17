from telethon import TelegramClient
from config import settings
import logging

logger = logging.getLogger(__name__)

async def create_session(phone, api_id, api_hash):
    client = TelegramClient(phone, api_id, api_hash)
    try:
        await client.connect()
        return client
    except Exception as e:
        logger.error("Error al crear la sesión: %s", e)
        return None

async def close_session(client):
    await client.disconnect()

async def sign_in_with_code(client, phone, code):
    try:
        await client.sign_in(phone, code)
        return True
    except Exception as e:
        logger.error(f"Error al iniciar sesión con el código: {str(e)}")
        return False

# Implement other Telegram-related functions here
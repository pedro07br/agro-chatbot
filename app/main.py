import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters
from dotenv import load_dotenv
from app.database import init_db
from app.bot import handle_update

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

telegram_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app

    print("=" * 40)
    print(
        f"🔍 TOKEN: {'OK - ' + TELEGRAM_TOKEN[:10] + '...' if TELEGRAM_TOKEN else 'VAZIO!'}")
    print(f"🔍 WEBHOOK_URL: '{WEBHOOK_URL}'")
    print("=" * 40)

    init_db()

    if WEBHOOK_URL:
        print("🌐 Modo WEBHOOK ativado")
        bot = Bot(token=TELEGRAM_TOKEN)
        webhook_endpoint = f"{WEBHOOK_URL}/webhook/{TELEGRAM_TOKEN}"
        await bot.set_webhook(url=webhook_endpoint)
        print(f"✅ Webhook registrado: {webhook_endpoint}")
    else:
        print("🔄 Modo POLLING ativado")

        async def message_handler(update: Update, context):
            await handle_update(update)

        telegram_app = (
            Application.builder()
            .token(TELEGRAM_TOKEN)
            .build()
        )

        telegram_app.add_handler(CommandHandler("start", message_handler))
        telegram_app.add_handler(CommandHandler("help", message_handler))
        telegram_app.add_handler(CommandHandler("limpar", message_handler))
        telegram_app.add_handler(MessageHandler(filters.TEXT, message_handler))

        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling(drop_pending_updates=True)
        print("✅ Polling iniciado! Bot online no Telegram.")

    yield

    if telegram_app:
        print("🔌 Encerrando polling...")
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
    elif WEBHOOK_URL:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.delete_webhook()
        print("🔌 Webhook removido")


app = FastAPI(
    title="AgroBot",
    description="Chatbot de agronegócio brasileiro",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {"status": "online", "bot": "AgroBot"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    if token != TELEGRAM_TOKEN:
        return {"error": "unauthorized"}, 401
    data = await request.json()
    update = Update.de_json(data, None)
    await handle_update(update)
    return {"ok": True}

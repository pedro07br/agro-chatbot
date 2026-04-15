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

telegram_app = None  # usado no modo polling


@asynccontextmanager
async def lifespan(app: FastAPI):
    # função que roda quando a API inicia e encerra

    global telegram_app

    # logs pra debug
    print("=" * 40)
    print(
        f"🔍 TOKEN: {'OK - ' + TELEGRAM_TOKEN[:10] + '...' if TELEGRAM_TOKEN else 'VAZIO!'}")
    print(f"🔍 WEBHOOK_URL: '{WEBHOOK_URL}'")
    print("=" * 40)

    init_db()  # inicializa banco (cria tabelas se não existir)

    if WEBHOOK_URL:
        # =========================
        # MODO WEBHOOK
        # =========================
        print("🌐 Modo WEBHOOK ativado")

        bot = Bot(token=TELEGRAM_TOKEN)

        # URL que o Telegram vai chamar
        webhook_endpoint = f"{WEBHOOK_URL}/webhook/{TELEGRAM_TOKEN}"

        # registrar webhook no Telegram
        await bot.set_webhook(url=webhook_endpoint)

        print(f"✅ Webhook registrado: {webhook_endpoint}")

    else:
        # =========================
        # MODO POLLING
        # =========================
        print("🔄 Modo POLLING ativado")

        # handler que chama a função principal
        async def message_handler(update: Update, context):
            await handle_update(update)

        # criar aplicação do Telegram
        telegram_app = (
            Application.builder()
            .token(TELEGRAM_TOKEN)
            .build()
        )

        # registrar comandos
        telegram_app.add_handler(CommandHandler("start", message_handler))
        telegram_app.add_handler(CommandHandler("help", message_handler))
        telegram_app.add_handler(CommandHandler("limpar", message_handler))

        # mensagens normais
        telegram_app.add_handler(MessageHandler(filters.TEXT, message_handler))

        # iniciar bot
        await telegram_app.initialize()
        await telegram_app.start()

        # iniciar polling (fica escutando mensagens)
        await telegram_app.updater.start_polling(drop_pending_updates=True)

        print("✅ Polling iniciado! Bot online no Telegram.")

    yield  # aqui a aplicação roda normalmente

    # =========================
    # ENCERRAMENTO
    # =========================

    if telegram_app:
        # parar polling
        print("🔌 Encerrando polling...")
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()

    elif WEBHOOK_URL:
        # remover webhook
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.delete_webhook()
        print("🔌 Webhook removido")


# criar API FastAPI
app = FastAPI(
    title="AgroBot",
    description="Chatbot de agronegócio brasileiro",
    version="1.0.0",
    lifespan=lifespan  # conecta ciclo de vida
)


@app.get("/")
async def root():
    # endpoint básico pra ver se tá online
    return {"status": "online", "bot": "AgroBot"}


@app.get("/health")
async def health():
    # endpoint de health check 
    return {"status": "healthy"}


@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    # endpoint que o Telegram chama no modo webhook

    # valida token
    if token != TELEGRAM_TOKEN:
        return {"error": "unauthorized"}, 401

    # pegar dados da requisição
    data = await request.json()

    # converter para objeto Update do Telegram
    update = Update.de_json(data, None)

    # processar mensagem
    await handle_update(update)

    return {"ok": True}  # resposta pro Telegram
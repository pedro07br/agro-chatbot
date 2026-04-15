import os 
from telegram import Update, Bot 
from telegram.constants import ChatAction
from dotenv import load_dotenv
from app.gemini import process_message

load_dotenv() 

# pegar token do bot 
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# criar instância do bot
bot = Bot(token=TELEGRAM_TOKEN)


async def handle_update(update: Update):
    """Processa mensagem recebida do Telegram"""

    # se não for mensagem de texto, ignora
    if not update.message or not update.message.text:
        return

    # dados básicos da conversa
    chat_id = update.message.chat_id
    user_name = update.message.from_user.first_name or "usuário"
    user_message = update.message.text

    # =========================
    # COMANDOS DO BOT
    # =========================

    if user_message.startswith("/start"):
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"Olá, {user_name}! Eu sou o AgroBot.\n\n"
                "Sou especializado em dados do agronegócio brasileiro. "
                "Posso te ajudar com:\n\n"
                "Produção agrícola por cultura e estado\n"
                "Exportações de commodities (soja, milho, café...)\n"
                "Histórico de produção agrícola\n"
                "Comparativo de produção entre anos\n\n"
                "Me faça uma pergunta! Por exemplo:\n"
                "Qual foi a produção de soja em 2022?\n"
                "Compare a produção de milho entre 2020 e 2022"
            )
        )
        return 

    if user_message.startswith("/help"):
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🤖 *Como usar o AgroBot*\n\n"
                "*Exportações:*\n"
                "• Qual foi a exportação de soja em 2021?\n"
                "• Histórico de preços do café de 2018 a 2021\n\n"
                "*Produção agrícola:*\n"
                "• Produção de milho por estado em 2021\n"
                "• Compare a produção de soja entre 2020 e 2021\n\n"
                "*Safras e estoques:*\n"
                "• Previsão de safra de trigo para 2021\n"
                "• Qual o estoque nacional de arroz?\n\n"
                "• Pesquisas de 2023 em diante estão disponíveis\n\n"
                "*Commodities disponíveis:*\n"
                "soja, milho, café, algodão, açúcar, "
                "carne bovina, frango, suíno, arroz, feijão, trigo"
            ),
            parse_mode="Markdown" 
        )
        return

    if user_message.startswith("/limpar"):
        await bot.send_message(
            chat_id=chat_id,
            text="🗑️ Histórico de conversa limpo! Pode começar uma nova consulta."
        )
        return

    # =========================
    # PROCESSAMENTO NORMAL
    # =========================

    # mostra "digitando..." pro usuário
    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        # chama IA pra interpretar e responder
        resposta = await process_message(chat_id, user_message)

        # envia resposta pro usuário
        await bot.send_message(
            chat_id=chat_id,
            text=resposta
        )

    except Exception as e:
        # debug mais completo no terminal
        import traceback
        print(f"ERRO COMPLETO:")
        print(traceback.format_exc())

        erro_str = str(e)

        if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
            msg_erro = (
                "⏳ Estou recebendo muitas perguntas no momento. "
                "Aguarde alguns segundos e tente novamente!"
            )

        elif "API key" in erro_str:
            msg_erro = "🔑 Erro de autenticação. Contate o administrador."

        else:
            msg_erro = "⚠️ Ocorreu um erro inesperado. Tente novamente em instantes."

        await bot.send_message(chat_id=chat_id, text=msg_erro)

        # log no console
        print(f"Erro ao processar mensagem do chat {chat_id}: {e}")
import os
from telegram import Update, Bot
from telegram.constants import ChatAction
from dotenv import load_dotenv
from app.gemini import process_message

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)


async def handle_update(update: Update):
    """Processa uma atualização recebida do Telegram."""

    # Ignora atualizações que não sejam mensagens de texto
    if not update.message or not update.message.text:
        return

    chat_id = update.message.chat_id
    user_name = update.message.from_user.first_name or "usuário"
    user_message = update.message.text

    # Comandos especiais
    if user_message.startswith("/start"):
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"👋 Olá, {user_name}! Eu sou o *AgroBot*.\n\n"
                "Sou especializado em dados do agronegócio brasileiro. "
                "Posso te ajudar com:\n\n"
                "🌱 *Produção agrícola* por cultura e estado\n"
                "📦 *Exportações* de commodities (soja, milho, café...)\n"
                "📈 *Histórico de preços* de exportação\n"
                "🌾 *Previsão de safras* e estoques nacionais\n\n"
                "Me faça uma pergunta! Por exemplo:\n"
                "_Qual foi a exportação de soja em 2023?_\n"
                "_Compare a produção de milho entre 2020 e 2023_"
            ),
            parse_mode="Markdown"
        )
        return

    if user_message.startswith("/help"):
        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🤖 *Como usar o AgroBot*\n\n"
                "*Exportações:*\n"
                "• Qual foi a exportação de soja em 2023?\n"
                "• Histórico de preços do café de 2018 a 2023\n\n"
                "*Produção agrícola:*\n"
                "• Produção de milho por estado em 2022\n"
                "• Compare a produção de soja entre 2020 e 2023\n\n"
                "*Safras e estoques:*\n"
                "• Previsão de safra de trigo para 2024\n"
                "• Qual o estoque nacional de arroz?\n\n"
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

    # Mostra "digitando..." enquanto processa
    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        resposta = await process_message(chat_id, user_message)
        await bot.send_message(
            chat_id=chat_id,
            text=resposta,
            parse_mode="Markdown"
        )
    except Exception as e:
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
        print(f"Erro ao processar mensagem do chat {chat_id}: {e}")

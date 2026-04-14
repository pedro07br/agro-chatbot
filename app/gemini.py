import os
import google.generativeai as genai
from dotenv import load_dotenv
from app.database import get_history, save_message
from app.tools import (
    get_exportacoes,
    get_historico_precos,
    get_producao_agricola,
    comparar_producao,
    get_safra,
    get_estoques,
)

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

TOOL_MAP = {
    "get_exportacoes": get_exportacoes,
    "get_historico_precos": get_historico_precos,
    "get_producao_agricola": get_producao_agricola,
    "comparar_producao": comparar_producao,
    "get_safra": get_safra,
    "get_estoques": get_estoques,
}

TOOLS = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="get_exportacoes",
            description="Retorna dados de exportacao brasileira de uma commodity agricola em um ano especifico.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "commodity": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Nome da commodity: soja, milho, cafe, algodao, acucar, carne_bovina, frango"
                    ),
                    "ano": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Ano da consulta. Ex: 2023"
                    ),
                },
                required=["commodity", "ano"]
            )
        ),
        genai.protos.FunctionDeclaration(
            name="get_historico_precos",
            description="Retorna historico de valores de exportacao de uma commodity entre dois anos.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "commodity": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Nome da commodity: soja, milho, cafe"
                    ),
                    "ano_inicio": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Ano de inicio do periodo"
                    ),
                    "ano_fim": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Ano de fim do periodo"
                    ),
                },
                required=["commodity", "ano_inicio", "ano_fim"]
            )
        ),
        genai.protos.FunctionDeclaration(
            name="get_producao_agricola",
            description="Retorna dados de producao agricola de uma cultura por estado brasileiro em um ano.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "cultura": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Nome da cultura: soja, milho, cafe, arroz, feijao, trigo"
                    ),
                    "ano": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Ano da consulta"
                    ),
                },
                required=["cultura", "ano"]
            )
        ),
        genai.protos.FunctionDeclaration(
            name="comparar_producao",
            description="Compara a producao agricola de uma cultura entre dois anos diferentes.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "cultura": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Nome da cultura: soja, milho, cafe"
                    ),
                    "ano_inicio": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Primeiro ano para comparacao"
                    ),
                    "ano_fim": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Segundo ano para comparacao"
                    ),
                },
                required=["cultura", "ano_inicio", "ano_fim"]
            )
        ),
        genai.protos.FunctionDeclaration(
            name="get_safra",
            description="Retorna dados de previsao e acompanhamento de safra de uma cultura em um ano.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "cultura": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Nome da cultura: soja, milho, cafe, trigo"
                    ),
                    "ano": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="Ano da safra"
                    ),
                },
                required=["cultura", "ano"]
            )
        ),
        genai.protos.FunctionDeclaration(
            name="get_estoques",
            description="Retorna dados de estoque nacional de uma cultura.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "cultura": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="Nome da cultura: soja, milho, arroz, feijao"
                    ),
                },
                required=["cultura"]
            )
        ),
    ]
)

SYSTEM_PROMPT = """
Você é o AgroBot, um assistente especializado em agronegócio brasileiro.
Você tem acesso a dados reais das seguintes fontes:
- ComexStat (Ministério da Economia): exportações e histórico de preços
- IBGE: produção agrícola por estado e comparativos anuais
- CONAB: previsão de safras e estoques nacionais

Sempre que o usuário fizer uma pergunta sobre dados agrícolas, use as 
ferramentas disponíveis para buscar informações reais antes de responder.

Ao responder:
- Seja objetivo e claro
- Cite sempre a fonte dos dados
- Use números formatados (ex: 1.234.567 toneladas)
- Se os dados não estiverem disponíveis, informe educadamente
- Responda sempre em português brasileiro
"""


async def process_message(chat_id: int, user_message: str) -> str:
    save_message(chat_id, "user", user_message)

    history = get_history(chat_id, limit=10)

    messages = []
    for msg in history[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        messages.append({"role": role, "parts": [msg["message"]]})

    messages.append({"role": "user", "parts": [user_message]})

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        tools=[TOOLS],
    )

    chat = model.start_chat(history=messages[:-1])
    response = await chat.send_message_async(user_message)

    # Verifica se o Gemini quer chamar uma ferramenta
    tool_results = []
    for part in response.parts:
        if hasattr(part, "function_call") and part.function_call.name:
            func_name = part.function_call.name
            func_args = dict(part.function_call.args)
            print(f"[TOOL] Chamando {func_name} com args: {func_args}")

            if func_name in TOOL_MAP:
                resultado = await TOOL_MAP[func_name](**func_args)
                tool_results.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=func_name,
                            response={"result": str(resultado)}
                        )
                    )
                )

    # Segunda chamada com os resultados das ferramentas
    if tool_results:
        response = await chat.send_message_async(tool_results)

    resposta = response.text
    save_message(chat_id, "assistant", resposta)
    return resposta

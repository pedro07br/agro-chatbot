import httpx
from app.database import get_cache, set_cache 

BASE_URL = "https://portaldeinformacoes.conab.gov.br/api"


# mapeamento das culturas
# aqui eu descobri que a API precisa desse formato específico
CULTURAS_CONAB = {
    "soja": "soja",
    "milho": "milho",
    "cafe": "cafe",
    "algodao": "algodao",
    "cana_de_acucar": "cana-de-acucar",
    "arroz": "arroz",
    "feijao": "feijao",
    "trigo": "trigo",
}


async def get_safra(cultura: str, ano: int) -> dict:
    ano = int(ano)  # garantir que não vem tipo 2022.0

    """
    pega dados de safra da CONAB (previsão e acompanhamento)
    """

    # chave do cache
    cache_key = f"conab:safra:{cultura}:{ano}"

    cached = get_cache(cache_key)
    if cached:
        return cached  # se já tiver salvo, nem chama a API

    # normalizar entrada do usuário
    cultura_lower = cultura.lower().replace(" ", "_").replace("-", "_")

    # pegar o valor que a API entende
    cultura_conab = CULTURAS_CONAB.get(cultura_lower)

    if not cultura_conab:
        return {
            "erro": f"Cultura '{cultura}' não encontrada na CONAB.",
            "disponiveis": list(CULTURAS_CONAB.keys())
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # fazer requisição pra API
            response = await client.get(
                f"{BASE_URL}/safras",
                params={
                    "cultura": cultura_conab,
                    "ano": ano,
                }
            )

            response.raise_for_status()  # se der erro já quebra aqui

            dados = response.json()  # converter resposta

        # montar resposta padrão
        resultado = {
            "cultura": cultura,
            "ano": ano,
            "fonte": "CONAB - Companhia Nacional de Abastecimento",
            "dados": dados
        }

        set_cache(cache_key, resultado, ttl_hours=6)  # salvar cache por 6h

        return resultado

    except httpx.HTTPError as e:
        # erro na API
        return {"erro": f"Falha ao consultar CONAB: {str(e)}"}


async def get_estoques(cultura: str) -> dict:
    """
    pega dados de estoque da CONAB
    """

    # cache sem ano pq é dado atual
    cache_key = f"conab:estoques:{cultura}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    # mesma lógica de normalização (talvez virar função depois)
    cultura_lower = cultura.lower().replace(" ", "_").replace("-", "_")
    cultura_conab = CULTURAS_CONAB.get(cultura_lower)

    if not cultura_conab:
        return {
            "erro": f"Cultura '{cultura}' não encontrada na CONAB.",
            "disponiveis": list(CULTURAS_CONAB.keys())
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{BASE_URL}/estoques",
                params={"cultura": cultura_conab}
            )

            response.raise_for_status()
            dados = response.json()

        resultado = {
            "cultura": cultura,
            "fonte": "CONAB - Companhia Nacional de Abastecimento",
            "dados": dados
        }

        set_cache(cache_key, resultado, ttl_hours=3)  # cache menor pq pode mudar mais

        return resultado

    except httpx.HTTPError as e:
        return {"erro": f"Falha ao consultar CONAB: {str(e)}"}
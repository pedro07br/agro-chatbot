import httpx
from app.database import get_cache, set_cache

BASE_URL = "https://portaldeinformacoes.conab.gov.br/api"

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
    ano = int(ano)
    """
    Retorna dados de previsão e acompanhamento de safra de uma cultura.
    Fonte: CONAB - Companhia Nacional de Abastecimento
    """
    cache_key = f"conab:safra:{cultura}:{ano}"

    cached = get_cache(cache_key)
    if cached:
        return cached

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
                f"{BASE_URL}/safras",
                params={
                    "cultura": cultura_conab,
                    "ano": ano,
                }
            )
            response.raise_for_status()
            dados = response.json()

        resultado = {
            "cultura": cultura,
            "ano": ano,
            "fonte": "CONAB - Companhia Nacional de Abastecimento",
            "dados": dados
        }

        set_cache(cache_key, resultado, ttl_hours=6)
        return resultado

    except httpx.HTTPError as e:
        return {"erro": f"Falha ao consultar CONAB: {str(e)}"}


async def get_estoques(cultura: str) -> dict:
    """
    Retorna dados de estoque nacional de uma cultura.
    Fonte: CONAB - Companhia Nacional de Abastecimento
    """
    cache_key = f"conab:estoques:{cultura}"

    cached = get_cache(cache_key)
    if cached:
        return cached

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

        set_cache(cache_key, resultado, ttl_hours=3)
        return resultado

    except httpx.HTTPError as e:
        return {"erro": f"Falha ao consultar CONAB: {str(e)}"}
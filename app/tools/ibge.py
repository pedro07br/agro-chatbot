import httpx
from app.database import get_cache, set_cache

BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"

# Código dos agregados IBGE para produção agrícola
AGREGADOS = {
    "area_plantada": "1612",
    "quantidade_produzida": "1613",
    "valor_producao": "1614",
}

# Principais culturas e seus códigos no IBGE
CULTURAS = {
    "soja": "109",
    "milho": "2713",
    "cafe": "2618",
    "algodao": "109",
    "cana_de_acucar": "2630",
    "arroz": "39432",
    "feijao": "109",
    "trigo": "2692",
}


async def get_producao_agricola(cultura: str, ano: int) -> dict:
    ano = int(ano)
    """
    Retorna dados de produção agrícola (área plantada, quantidade e valor)
    de uma cultura em um ano específico, por estado.
    Fonte: IBGE - Pesquisa Agrícola Municipal (PAM)
    """
    cache_key = f"ibge:producao:{cultura}:{ano}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    cultura_lower = cultura.lower().replace(" ", "_").replace("-", "_")
    codigo_cultura = CULTURAS.get(cultura_lower)

    if not codigo_cultura:
        return {
            "erro": f"Cultura '{cultura}' não encontrada.",
            "disponiveis": list(CULTURAS.keys())
        }

    try:
        resultados = {}

        async with httpx.AsyncClient(timeout=30) as client:
            for nome_agregado, codigo_agregado in AGREGADOS.items():
                response = await client.get(
                    f"{BASE_URL}/{codigo_agregado}/periodos/{ano}/variaveis/{codigo_cultura}",
                    params={
                        "localidades": "N3[all]",  # todos os estados
                        "classificacao": "782[allxt]"
                    }
                )
                if response.status_code == 200:
                    resultados[nome_agregado] = response.json()

        resultado = {
            "cultura": cultura,
            "ano": ano,
            "fonte": "IBGE - Pesquisa Agrícola Municipal (PAM)",
            "dados": resultados
        }

        set_cache(cache_key, resultado, ttl_hours=12)
        return resultado

    except httpx.HTTPError as e:
        return {"erro": f"Falha ao consultar IBGE: {str(e)}"}


async def comparar_producao(cultura: str, ano_inicio: int, ano_fim: int) -> dict:
    ano_inicio = int(ano_inicio)
    ano_fim = int(ano_fim)
    """
    Compara a produção agrícola de uma cultura entre dois anos.
    Fonte: IBGE - Pesquisa Agrícola Municipal (PAM)
    """
    cache_key = f"ibge:comparar:{cultura}:{ano_inicio}:{ano_fim}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    cultura_lower = cultura.lower().replace(" ", "_").replace("-", "_")
    codigo_cultura = CULTURAS.get(cultura_lower)

    if not codigo_cultura:
        return {
            "erro": f"Cultura '{cultura}' não encontrada.",
            "disponiveis": list(CULTURAS.keys())
        }

    try:
        periodos = f"{ano_inicio}|{ano_fim}"
        comparativo = {}

        async with httpx.AsyncClient(timeout=30) as client:
            for nome_agregado, codigo_agregado in AGREGADOS.items():
                response = await client.get(
                    f"{BASE_URL}/{codigo_agregado}/periodos/{periodos}/variaveis/{codigo_cultura}",
                    params={"localidades": "N1[all]"}  # nível Brasil
                )
                if response.status_code == 200:
                    comparativo[nome_agregado] = response.json()

        resultado = {
            "cultura": cultura,
            "periodo": f"{ano_inicio} vs {ano_fim}",
            "fonte": "IBGE - Pesquisa Agrícola Municipal (PAM)",
            "comparativo": comparativo
        }

        set_cache(cache_key, resultado, ttl_hours=12)
        return resultado

    except httpx.HTTPError as e:
        return {"erro": f"Falha ao consultar IBGE: {str(e)}"}
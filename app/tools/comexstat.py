import httpx
from app.database import get_cache, set_cache

BASE_SIDRA = "https://apisidra.ibge.gov.br/values"

COMMODITIES = {
    "soja": "40124",
    "milho": "40122",
    "cafe": "40139",
    "algodao": "40099",
    "cana_de_acucar": "40106",
    "arroz": "40102",
    "feijao": "40112",
    "trigo": "40127",
    "mandioca": "40119",
    "laranja": "40151",
    "banana": "40136",
}


async def get_exportacoes(commodity: str, ano: int) -> dict:
    """
    Retorna dados de produção de uma commodity em um ano específico.
    Fonte: IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)
    """
    ano = int(ano)
    commodity_lower = (
        commodity.lower()
        .replace(" ", "_")
        .replace("ç", "c")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("á", "a")
        .replace("ó", "o")
        .replace("í", "i")
    )
    cache_key = f"sidra:prod:{commodity_lower}:{ano}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    codigo = COMMODITIES.get(commodity_lower)
    if not codigo:
        return {
            "commodity": commodity,
            "erro": f"Commodity '{commodity}' não encontrada.",
            "disponiveis": list(COMMODITIES.keys())
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Busca quantidade produzida (v/214) e área plantada (v/109)
            url_qtd = f"{BASE_SIDRA}/t/5457/n1/all/v/214/p/{ano}/c782/{codigo}"
            url_area = f"{BASE_SIDRA}/t/5457/n1/all/v/109/p/{ano}/c782/{codigo}"
            url_valor = f"{BASE_SIDRA}/t/5457/n1/all/v/215/p/{ano}/c782/{codigo}"

            r_qtd = await client.get(url_qtd)
            r_area = await client.get(url_area)
            r_valor = await client.get(url_valor)

            def extrair(response):
                if response.status_code == 200 and response.content:
                    dados = response.json()
                    for item in dados:
                        if isinstance(item, dict) and item.get("V") not in ("...", "-", "", None, "0"):
                            return {
                                "valor": item.get("V"),
                                "unidade": item.get("MN"),
                                "cultura": item.get("D4N") or commodity
                            }
                return None

            qtd = extrair(r_qtd)
            area = extrair(r_area)
            valor = extrair(r_valor)

            if not qtd and not area:
                return {
                    "commodity": commodity,
                    "ano": ano,
                    "fonte": "IBGE SIDRA - PAM",
                    "mensagem": f"Dados de {ano} ainda não disponíveis. Tente {ano - 1}."
                }

            resultado = {
                "commodity": commodity,
                "ano": ano,
                "fonte": "IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)",
                "quantidade_produzida": qtd,
                "area_plantada": area,
                "valor_producao": valor
            }

        set_cache(cache_key, resultado, ttl_hours=6)
        return resultado

    except Exception as e:
        return {"erro": f"Erro ao consultar IBGE SIDRA: {str(e)}"}


async def get_historico_precos(commodity: str, ano_inicio: int, ano_fim: int) -> dict:
    """
    Retorna histórico de produção de uma commodity entre dois anos.
    Fonte: IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)
    """
    ano_inicio = int(ano_inicio)
    ano_fim = int(ano_fim)
    cache_key = f"sidra:historico:{commodity}:{ano_inicio}:{ano_fim}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    commodity_lower = commodity.lower().replace(" ", "_").replace("ç", "c").replace("ã", "a")
    codigo = COMMODITIES.get(commodity_lower)

    if not codigo:
        return {
            "commodity": commodity,
            "erro": f"Commodity '{commodity}' não encontrada.",
            "disponiveis": list(COMMODITIES.keys())
        }

    try:
        anos = ",".join(str(a) for a in range(ano_inicio, ano_fim + 1))

        async with httpx.AsyncClient(timeout=30) as client:
            url = f"{BASE_SIDRA}/t/5457/n1/all/v/214/p/{anos}/c782/{codigo}"
            response = await client.get(url)

            if response.status_code != 200 or not response.content:
                return {"erro": "API SIDRA indisponível"}

            dados = response.json()
            historico = {}
            for item in dados:
                if isinstance(item, dict) and item.get("V") not in ("...", "-", "", None):
                    ano = item.get("D3N", "?")
                    historico[ano] = {
                        "quantidade": item.get("V"),
                        "unidade": item.get("MN"),
                        "cultura": item.get("D4N") or commodity
                    }

            resultado = {
                "commodity": commodity,
                "periodo": f"{ano_inicio} a {ano_fim}",
                "fonte": "IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)",
                "historico": historico
            }

        set_cache(cache_key, resultado, ttl_hours=12)
        return resultado

    except Exception as e:
        return {"erro": f"Erro ao consultar IBGE SIDRA: {str(e)}"}
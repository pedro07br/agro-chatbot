import httpx
from app.database import get_cache, set_cache

BASE_SIDRA = "https://apisidra.ibge.gov.br/values"

CULTURAS = {
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

# Códigos dos estados brasileiros no IBGE
ESTADOS = {
    "AC": "12", "AL": "27", "AP": "16", "AM": "13", "BA": "29",
    "CE": "23", "DF": "53", "ES": "32", "GO": "52", "MA": "21",
    "MT": "51", "MS": "50", "MG": "31", "PA": "15", "PB": "25",
    "PR": "41", "PE": "26", "PI": "22", "RJ": "33", "RN": "24",
    "RS": "43", "RO": "11", "RR": "14", "SC": "42", "SP": "35",
    "SE": "28", "TO": "17"
}


async def get_producao_agricola(cultura: str, ano: int) -> dict:
    """
    Retorna dados de produção agrícola de uma cultura por estado em um ano.
    Fonte: IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)
    """
    ano = int(ano)
    cultura_lower = (
        cultura.lower()
        .replace(" ", "_")
        .replace("ç", "c")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("á", "a")
    )
    cache_key = f"ibge:estados:{cultura_lower}:{ano}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    codigo = CULTURAS.get(cultura_lower)
    if not codigo:
        return {
            "erro": f"Cultura '{cultura}' não encontrada.",
            "disponiveis": list(CULTURAS.keys())
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Busca por estado (N3 = estados)
            url = f"{BASE_SIDRA}/t/5457/n3/all/v/214/p/{ano}/c782/{codigo}"
            response = await client.get(url)

            if response.status_code != 200 or not response.content:
                return {
                    "cultura": cultura,
                    "ano": ano,
                    "mensagem": "API indisponível"
                }

            dados = response.json()

            estados_resultado = []
            for item in dados:
                if isinstance(item, dict) and item.get("V") not in ("...", "-", "", None):
                    estados_resultado.append({
                        "estado": item.get("D1N"),
                        "quantidade": item.get("V"),
                        "unidade": item.get("MN")
                    })

            # Ordena por quantidade decrescente
            estados_resultado.sort(
                key=lambda x: float(x["quantidade"].replace(".", "").replace(",", "."))
                if x["quantidade"].replace(".", "").replace(",", ".").replace("-", "").isdigit()
                else 0,
                reverse=True
            )

            if not estados_resultado:
                return {
                    "cultura": cultura,
                    "ano": ano,
                    "fonte": "IBGE SIDRA - PAM",
                    "mensagem": f"Dados de {ano} indisponíveis. Tente {ano - 1}."
                }

            resultado = {
                "cultura": cultura,
                "ano": ano,
                "fonte": "IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)",
                "top_estados": estados_resultado[:10],
                "total_estados": len(estados_resultado)
            }

        set_cache(cache_key, resultado, ttl_hours=12)
        return resultado

    except Exception as e:
        return {"erro": f"Erro ao consultar IBGE SIDRA: {str(e)}"}


async def comparar_producao(cultura: str, ano_inicio: int, ano_fim: int) -> dict:
    """
    Compara a produção agrícola de uma cultura entre dois anos.
    Fonte: IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)
    """
    ano_inicio = int(ano_inicio)
    ano_fim = int(ano_fim)
    cache_key = f"ibge:comparar:{cultura}:{ano_inicio}:{ano_fim}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    cultura_lower = cultura.lower().replace(" ", "_").replace("ç", "c").replace("ã", "a")
    codigo = CULTURAS.get(cultura_lower)

    if not codigo:
        return {
            "erro": f"Cultura '{cultura}' não encontrada.",
            "disponiveis": list(CULTURAS.keys())
        }

    try:
        anos = f"{ano_inicio},{ano_fim}"

        async with httpx.AsyncClient(timeout=30) as client:
            url = f"{BASE_SIDRA}/t/5457/n1/all/v/214/p/{anos}/c782/{codigo}"
            response = await client.get(url)

            if response.status_code != 200 or not response.content:
                return {"erro": "API SIDRA indisponível"}

            dados = response.json()

            comparativo = {}
            for item in dados:
                if isinstance(item, dict) and item.get("V") not in ("...", "-", "", None):
                    ano = item.get("D3N", "?")
                    comparativo[ano] = {
                        "quantidade": item.get("V"),
                        "unidade": item.get("MN"),
                        "cultura": item.get("D4N") or cultura
                    }

            if not comparativo:
                return {
                    "cultura": cultura,
                    "periodo": f"{ano_inicio} vs {ano_fim}",
                    "mensagem": "Dados indisponíveis para comparação."
                }

            resultado = {
                "cultura": cultura,
                "periodo": f"{ano_inicio} vs {ano_fim}",
                "fonte": "IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)",
                "comparativo": comparativo
            }

        set_cache(cache_key, resultado, ttl_hours=12)
        return resultado

    except Exception as e:
        return {"erro": f"Erro ao consultar IBGE SIDRA: {str(e)}"}
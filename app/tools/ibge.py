import httpx
from app.database import get_cache, set_cache

# URL base da API do IBGE SIDRA
BASE_SIDRA = "https://apisidra.ibge.gov.br/values"


# mapeamento das culturas → código que o IBGE usa internamente
# isso aqui tive que descobrir/testar na API
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

# códigos dos estados no IBGE (talvez usar isso depois pra filtro)
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
    pega produção agrícola por estado
    """

    ano = int(ano)  # garantir tipo int (às vezes vem float)

    # normalizar entrada do usuário
    cultura_lower = (
        cultura.lower()
        .replace(" ", "_")
        .replace("ç", "c")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("á", "a")
    )

    # chave do cache
    cache_key = f"ibge:estados:{cultura_lower}:{ano}"

    cached = get_cache(cache_key)
    if cached:
        return cached  # evita chamada na API

    # pegar código da cultura
    codigo = CULTURAS.get(cultura_lower)

    if not codigo:
        return {
            "erro": f"Cultura '{cultura}' não encontrada.",
            "disponiveis": list(CULTURAS.keys())
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:

            # N3 = nível de estado (isso aqui é importante lembrar)
            url = f"{BASE_SIDRA}/t/5457/n3/all/v/214/p/{ano}/c782/{codigo}"

            response = await client.get(url)

            # validação básica da resposta
            if response.status_code != 200 or not response.content:
                return {
                    "cultura": cultura,
                    "ano": ano,
                    "mensagem": "API indisponível"
                }

            dados = response.json()

            estados_resultado = []

            # percorrer dados e filtrar valores válidos
            for item in dados:
                if isinstance(item, dict) and item.get("V") not in ("...", "-", "", None):
                    estados_resultado.append({
                        "estado": item.get("D1N"),  # nome do estado
                        "quantidade": item.get("V"),
                        "unidade": item.get("MN")
                    })

            # ordenar do maior pro menor
            # converter string tipo "1.234,56" → float
            estados_resultado.sort(
                key=lambda x: float(x["quantidade"].replace(".", "").replace(",", "."))
                if x["quantidade"].replace(".", "").replace(",", ".").replace("-", "").isdigit()
                else 0,
                reverse=True
            )

            # se não tiver dados
            if not estados_resultado:
                return {
                    "cultura": cultura,
                    "ano": ano,
                    "fonte": "IBGE SIDRA - PAM",
                    "mensagem": f"Dados de {ano} indisponíveis. Tente {ano - 1}."
                }

            # resposta final
            resultado = {
                "cultura": cultura,
                "ano": ano,
                "fonte": "IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)",
                "top_estados": estados_resultado[:10],  # pegar só os 10 maiores
                "total_estados": len(estados_resultado)
            }

        set_cache(cache_key, resultado, ttl_hours=12)  # cache maior pq não muda rápido

        return resultado

    except Exception as e:
        # erro genérico
        return {"erro": f"Erro ao consultar IBGE SIDRA: {str(e)}"}


async def comparar_producao(cultura: str, ano_inicio: int, ano_fim: int) -> dict:
    """
    compara produção entre dois anos
    """

    ano_inicio = int(ano_inicio)
    ano_fim = int(ano_fim)

    cache_key = f"ibge:comparar:{cultura}:{ano_inicio}:{ano_fim}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    # normalização
    cultura_lower = cultura.lower().replace(" ", "_").replace("ç", "c").replace("ã", "a")

    codigo = CULTURAS.get(cultura_lower)

    if not codigo:
        return {
            "erro": f"Cultura '{cultura}' não encontrada.",
            "disponiveis": list(CULTURAS.keys())
        }

    try:
        # montar anos tipo "2020,2023"
        anos = f"{ano_inicio},{ano_fim}"

        async with httpx.AsyncClient(timeout=30) as client:
            url = f"{BASE_SIDRA}/t/5457/n1/all/v/214/p/{anos}/c782/{codigo}"
            response = await client.get(url)

            if response.status_code != 200 or not response.content:
                return {"erro": "API SIDRA indisponível"}

            dados = response.json()

            comparativo = {}

            # montar comparação ano → valor
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
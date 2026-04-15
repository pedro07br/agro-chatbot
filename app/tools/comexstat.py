import httpx  # Cliente HTTP assíncrono (melhor que requests pra esse tipo de API async)
from app.database import get_cache, set_cache  # Funções pra evitar chamadas repetidas na API

# URL base da API do SIDRA (IBGE)
BASE_SIDRA = "https://apisidra.ibge.gov.br/values"


# Esse dicionário é basicamente um "tradutor":
# o usuário fala "soja", mas a API do IBGE entende "40124"
# então a gente faz esse mapeamento manual aqui
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
    Busca dados de produção agrícola de uma commodity em um ano específico.
    Aqui a gente consulta diretamente o SIDRA (IBGE).
    """

    # Garantia de tipo: às vezes vem float tipo 2022.0
    ano = int(ano)

    # Normaliza o nome da commodity pra evitar erro de escrita do usuário
    # Ex: "Café" -> "cafe", "Cana de Açúcar" -> "cana_de_acucar"
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

    # Monta uma chave única pra cache (tipo um identificador da consulta)
    cache_key = f"sidra:prod:{commodity_lower}:{ano}"

    # Primeiro tenta pegar do cache
    cached = get_cache(cache_key)
    if cached:
        return cached  # Se já tiver, nem continua — retorna direto

    # Pega o código interno da commodity
    codigo = COMMODITIES.get(commodity_lower)
    if not codigo:
        # Caso a commodity não exista no dicionário
        return {
            "commodity": commodity,
            "erro": f"Commodity '{commodity}' não encontrada.",
            "disponiveis": list(COMMODITIES.keys())
        }

    try:
        # Cria cliente HTTP assíncrono com timeout
        async with httpx.AsyncClient(timeout=30) as client:

            # Monta URLs pra diferentes métricas
            # v/214 = quantidade produzida
            # v/109 = área plantada
            # v/215 = valor da produção
            url_qtd = f"{BASE_SIDRA}/t/5457/n1/all/v/214/p/{ano}/c782/{codigo}"
            url_area = f"{BASE_SIDRA}/t/5457/n1/all/v/109/p/{ano}/c782/{codigo}"
            url_valor = f"{BASE_SIDRA}/t/5457/n1/all/v/215/p/{ano}/c782/{codigo}"

            # Faz as requisições 
            r_qtd = await client.get(url_qtd)
            r_area = await client.get(url_area)
            r_valor = await client.get(url_valor)

            # Função interna pra extrair dados úteis da resposta da API
            def extrair(response):
                # Verifica se veio resposta válida
                if response.status_code == 200 and response.content:
                    dados = response.json()

                    # Percorre os dados até achar um valor válido
                    for item in dados:
                        if isinstance(item, dict) and item.get("V") not in ("...", "-", "", None, "0"):
                            return {
                                "valor": item.get("V"),
                                "unidade": item.get("MN"),
                                "cultura": item.get("D4N") or commodity
                            }
                return None  # Se não encontrou nada útil

            # Extrai cada tipo de dado
            qtd = extrair(r_qtd)
            area = extrair(r_area)
            valor = extrair(r_valor)

            # Se não tem dados básicos, provavelmente o ano ainda não foi publicado
            if not qtd and not area:
                return {
                    "commodity": commodity,
                    "ano": ano,
                    "fonte": "IBGE SIDRA - PAM",
                    "mensagem": f"Dados de {ano} ainda não disponíveis. Tente {ano - 1}."
                }

            # Monta resposta final estruturada
            resultado = {
                "commodity": commodity,
                "ano": ano,
                "fonte": "IBGE SIDRA - Pesquisa Agrícola Municipal (PAM)",
                "quantidade_produzida": qtd,
                "area_plantada": area,
                "valor_producao": valor
            }

        # Salva no cache por 6 horas
        set_cache(cache_key, resultado, ttl_hours=6)

        return resultado

    except Exception as e:
        # Tratamento genérico de erro
        return {"erro": f"Erro ao consultar IBGE SIDRA: {str(e)}"}


async def get_historico_precos(commodity: str, ano_inicio: int, ano_fim: int) -> dict:
    """
    Retorna o histórico de produção de uma commodity entre dois anos.
    """

    ano_inicio = int(ano_inicio)
    ano_fim = int(ano_fim)

    # Chave de cache única pra esse intervalo
    cache_key = f"sidra:historico:{commodity}:{ano_inicio}:{ano_fim}"

    # Verifica cache antes de tudo
    cached = get_cache(cache_key)
    if cached:
        return cached

    # Normalização básica
    commodity_lower = commodity.lower().replace(" ", "_").replace("ç", "c").replace("ã", "a")

    # Busca código da commodity
    codigo = COMMODITIES.get(commodity_lower)

    if not codigo:
        return {
            "commodity": commodity,
            "erro": f"Commodity '{commodity}' não encontrada.",
            "disponiveis": list(COMMODITIES.keys())
        }

    try:
        # Cria string tipo: "2019,2020,2021,2022"
        anos = ",".join(str(a) for a in range(ano_inicio, ano_fim + 1))

        async with httpx.AsyncClient(timeout=30) as client:
            # Aqui buscamos apenas quantidade produzida ao longo do tempo
            url = f"{BASE_SIDRA}/t/5457/n1/all/v/214/p/{anos}/c782/{codigo}"
            response = await client.get(url)

            # Validação básica da resposta
            if response.status_code != 200 or not response.content:
                return {"erro": "API SIDRA indisponível"}

            dados = response.json()
            historico = {}

            # Monta um dicionário ano -> dados
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

        # histórico muda menos
        set_cache(cache_key, resultado, ttl_hours=12)

        return resultado

    except Exception as e:
        return {"erro": f"Erro ao consultar IBGE SIDRA: {str(e)}"}
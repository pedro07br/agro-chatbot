# 🌾 AgroBot — Chatbot de Agronegócio Brasileiro

Chatbot de inteligência artificial especializado em dados do agronegócio brasileiro, integrado ao Telegram e alimentado por APIs públicas do governo federal.

---

## 🤖 O que o bot faz

O AgroBot responde perguntas em linguagem natural sobre o agronegócio brasileiro. O usuário escreve uma pergunta no Telegram e o bot consulta automaticamente as APIs públicas certas, processa os dados e responde de forma clara.

**Exemplos de perguntas:**
- _Qual foi a produção de soja em 2022?_
- _Histórico de produção do milho de 2019 a 2022_
- _Compare a produção de café entre 2018 e 2022_
- _Qual a previsão de safra de trigo para 2024?_
- _Qual o estoque nacional de arroz?_

---

## ⚙️ Funcionalidades

| Função | Descrição | Fonte |
|--------|-----------|-------|
| Produção de commodities | Quantidade produzida, área plantada e valor por ano | IBGE SIDRA |
| Histórico de produção | Evolução da produção entre dois anos | IBGE SIDRA |
| Produção por estado | Dados por cultura e estado brasileiro | IBGE PAM |
| Previsão de safras | Acompanhamento e estimativas de colheita | CONAB |
| Estoques nacionais | Disponibilidade e reservas por cultura | CONAB |

**Commodities disponíveis:**
`soja` `milho` `cafe` `algodao` `cana_de_acucar` `arroz` `feijao` `trigo` `mandioca` `laranja` `banana`

---

## 🏗️ Arquitetura

Usuário
│
▼
Telegram
│
▼
FastAPI (Polling / Webhook)
│
▼
Gemini 2.5 Flash (Tool Calling)
│
├──▶ IBGE SIDRA — produção agrícola
├──▶ IBGE PAM   — produção por estado
└──▶ CONAB      — safras e estoques
│
▼
MySQL — cache de consultas + histórico de conversas

O Gemini interpreta a pergunta do usuário, decide qual API consultar, busca os dados reais e formula uma resposta em português.

---

## 🛠️ Tecnologias utilizadas

| Tecnologia | Versão | Função |
|-----------|--------|--------|
| Python | 3.11 | Linguagem principal |
| FastAPI | 0.111.0 | API REST e recebimento do webhook |
| Uvicorn | 0.30.1 | Servidor ASGI assíncrono |
| python-telegram-bot | 21.3 | Integração com a API do Telegram |
| Google Gemini 2.5 Flash | — | LLM com tool calling para orquestração |
| MySQL | 8.0 | Cache de consultas e histórico de conversas |
| Docker + Docker Compose | — | Containerização e orquestração |
| httpx | 0.27.0 | Requisições HTTP assíncronas às APIs |
| python-dotenv | 1.0.1 | Leitura de variáveis de ambiente |

---

## 📁 Estrutura do projeto

agro-chatbot/
├── docker-compose.yml       # Orquestra os containers (app + MySQL)
├── Dockerfile               # Imagem da aplicação Python
├── .env                     # Variáveis de ambiente (não versionar)
├── requirements.txt         # Dependências Python
└── app/
├── main.py              # FastAPI + inicialização do polling/webhook
├── bot.py               # Recebe e processa mensagens do Telegram
├── gemini.py            # Integração com Gemini + tool calling
├── database.py          # Conexão MySQL, histórico e cache
└── tools/
├── init.py      # Exporta todas as funções das ferramentas
├── comexstat.py     # Consultas à API IBGE SIDRA
├── ibge.py          # Produção agrícola por estado (IBGE PAM)
└── conab.py         # Safras e estoques (CONAB)

---

## 🗄️ Banco de dados

O MySQL roda na porta **3309** externamente e **3306** internamente no Docker.

### Tabela `conversations`
Armazena o histórico de mensagens de cada usuário para manter contexto na conversa.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INT | Chave primária |
| chat_id | BIGINT | ID do chat no Telegram |
| role | VARCHAR(20) | `user` ou `assistant` |
| message | TEXT | Conteúdo da mensagem |
| created_at | DATETIME | Data e hora do registro |

### Tabela `api_cache`
Armazena respostas das APIs com tempo de expiração para evitar requisições repetidas.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INT | Chave primária |
| cache_key | VARCHAR(255) | Identificador único da consulta |
| response | LONGTEXT | Resposta serializada em JSON |
| created_at | DATETIME | Data de criação |
| expires_at | DATETIME | Data de expiração do cache |

---

## 🚀 Como rodar o projeto

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- Conta no [Google AI Studio](https://aistudio.google.com) para obter a chave do Gemini
- Bot criado no Telegram via [@BotFather](https://t.me/BotFather)

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/agro-chatbot.git
cd agro-chatbot
```

### 2. Configure as variáveis de ambiente

Crie o arquivo `.env` na raiz do projeto:

```env
TELEGRAM_TOKEN=seu_token_aqui
GEMINI_API_KEY=sua_chave_aqui
MYSQL_ROOT_PASSWORD=
MYSQL_DATABASE=agrobot
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_HOST=db
MYSQL_PORT=3306
WEBHOOK_URL=
```

> Deixe `WEBHOOK_URL` vazio para rodar em modo polling (desenvolvimento local).

### 3. Suba os containers

```bash
docker compose up --build
```

O banco de dados será inicializado automaticamente na primeira execução.

### 4. Acesse o bot

Abra o Telegram, encontre seu bot pelo username e envie `/start`.

---

## 💬 Comandos disponíveis

| Comando | Descrição |
|---------|-----------|
| `/start` | Apresentação do bot e instruções |
| `/help` | Lista de exemplos de perguntas |
| `/limpar` | Limpa o histórico da conversa |

---

## 🔧 Comandos úteis do Docker

```bash
# Acompanhar logs em tempo real
docker compose logs app -f

# Acessar o container da aplicação
docker compose exec app bash

# Acessar o banco de dados
docker compose exec db mysql -u root agrobot

# Parar os containers
docker compose down

# Parar e apagar os dados do banco
docker compose down -v
```

---

## 🤖 Uso de IA no desenvolvimento

Este projeto foi desenvolvido em colaboração com **Claude (Anthropic)**.

### O que foi desenvolvido pelo autor
- Definição da arquitetura e escolha das tecnologias
- Escolha e validação das APIs públicas (IBGE SIDRA, CONAB)
- Configuração do ambiente Docker e MySQL na porta 3309
- Testes das APIs e identificação dos códigos corretos das culturas
- Decisão das funcionalidades e escopo do chatbot

### O que foi assistido por IA
- Geração dos arquivos base (`main.py`, `bot.py`, `gemini.py`, `database.py`)
- Estrutura do projeto e arquivos de configuração Docker
- Implementação do tool calling com o Gemini
- Debugging de erros de conexão, integração e compatibilidade de APIs
- Escrita e formatação deste README

### Decisões técnicas com apoio de IA
- Uso de **polling** para desenvolvimento local e **webhook** para produção
- Estratégia de **cache no MySQL** para otimizar chamadas às APIs públicas
- Uso de **tool calling** do Gemini para orquestração inteligente das funções
- Escolha da **tabela 5457 do IBGE SIDRA** após testes com múltiplos endpoints
- Implementação de **retry automático** na conexão com MySQL para evitar falhas no startup do Docker

---

## ⚠️ Limitações conhecidas

- O plano gratuito do Gemini possui limite de requisições por dia — em produção recomenda-se um plano pago
- Dados do IBGE para o ano corrente podem estar indisponíveis (`...`) enquanto não publicados
- O modo polling não é recomendado para produção — configure `WEBHOOK_URL` com uma URL pública HTTPS
- A API da CONAB pode apresentar instabilidades ocasionais

---

## 📄 Licença

MIT
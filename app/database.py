import mysql.connector
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    # cria conexão com o banco usando variáveis de ambiente
    # se não tiver variável, usa valor padrão
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "db"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "agrobot"),
    )


def wait_for_db(retries: int = 10, delay: int = 3):
    # tenta conectar várias vezes
    for attempt in range(retries):
        try:
            conn = mysql.connector.connect(
                host=os.getenv("MYSQL_HOST", "db"),
                port=int(os.getenv("MYSQL_PORT", 3306)),
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", ""),
            )
            conn.close()

            print("[OK] MySQL disponivel!")
            return True
        
        except Exception as e:
            print(f"[WAIT] Aguardando MySQL... tentativa {attempt + 1}/{retries} - {e}")
            time.sleep(delay)
    raise Exception("[ERRO] Nao foi possivel conectar ao MySQL.")


def init_db():
    print("[INFO] Iniciando banco de dados...")
    wait_for_db() 
    print("[INFO] Conectado! Criando tabelas...")
    conn = get_connection()


def init_db():
    """Aguarda o banco e cria as tabelas se não existirem."""
    wait_for_db()  # garantir que o banco está disponível

    conn = get_connection()
    cursor = conn.cursor()

    # tabela de conversas (histórico do chat)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            chat_id     BIGINT       NOT NULL,
            role        VARCHAR(20)  NOT NULL,  -- user ou assistant
            message     TEXT         NOT NULL,
            created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_chat_id (chat_id)
        )
    """)

    # tabela de cache (guardar respostas de API)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            cache_key   VARCHAR(255) NOT NULL UNIQUE,  -- chave única
            response    LONGTEXT     NOT NULL,         -- resposta em JSON
            created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
            expires_at  DATETIME     NOT NULL,
            INDEX idx_cache_key (cache_key),
            INDEX idx_expires_at (expires_at)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ Banco de dados inicializado com sucesso!")


# ─── Funções de conversa ───────────────────────────────────────────────────────

def save_message(chat_id: int, role: str, message: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO conversations (chat_id, role, message) VALUES (%s, %s, %s)",
        (chat_id, role, message)
    )

    conn.commit()
    cursor.close()
    conn.close()


def get_history(chat_id: int, limit: int = 10) -> list[dict]:
    # busca últimas mensagens do chat
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)  # retorna como dict

    cursor.execute(
        """
        SELECT role, message FROM conversations
        WHERE chat_id = %s
        ORDER BY created_at DESC  -- mais recentes primeiro
        LIMIT %s
        """,
        (chat_id, limit)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    # inverter lista pra ficar na ordem correta (antigo → novo)
    return list(reversed(rows))


# ─── Funções de cache ──────────────────────────────────────────────────────────

def get_cache(key: str) -> dict | None:
    # busca cache válido
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT response FROM api_cache
        WHERE cache_key = %s AND expires_at > NOW()
        """,
        (key,)
    )

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row:
        # converter JSON string para dict
        return json.loads(row["response"])

    return None  # não encontrou ou expirou


def set_cache(key: str, data: dict, ttl_hours: int = 6):
    # salva ou atualiza cache no banco
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO api_cache (cache_key, response, expires_at)
        VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL %s HOUR))
        ON DUPLICATE KEY UPDATE
            response   = VALUES(response),  -- atualiza resposta
            created_at = NOW(),
            expires_at = DATE_ADD(NOW(), INTERVAL %s HOUR)
        """,
        (key, json.dumps(data), ttl_hours, ttl_hours)
    )

    conn.commit()
    cursor.close()
    conn.close()
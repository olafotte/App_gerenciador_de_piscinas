import sqlite3
from datetime import datetime
import hashlib
import os

DB_NAME = "piscina_data.db"


def get_connection():
    url = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")
    if url and auth_token:
        try:
            from libsql import connect
            return connect(url, auth_token=auth_token)
        except Exception as exc:
            print(f"Remote database unavailable, falling back to local SQLite: {exc}")
    return sqlite3.connect(DB_NAME)


def _create_schema(conn):
    cursor = conn.cursor()

    # Tabela para usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            salt BLOB NOT NULL,
            password_hash BLOB NOT NULL
        )
    ''')

    # Tabela para piscinas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            volume REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Tabela para armazenar o histórico
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pool_id INTEGER,
            data_hora TEXT,
            responsavel TEXT,
            ph REAL,
            cloro REAL,
            generator_level INTEGER DEFAULT 0,
            alcalinidade INTEGER,
            dureza INTEGER,
            salinidade INTEGER,
            FOREIGN KEY (pool_id) REFERENCES pools(id)
        )
    ''')

    cursor.execute("PRAGMA table_info(medicoes)")
    columns = [row[1] for row in cursor.fetchall()]
    if "generator_level" not in columns:
        cursor.execute("ALTER TABLE medicoes ADD COLUMN generator_level INTEGER DEFAULT 0")
    if "pool_id" not in columns:
        cursor.execute("ALTER TABLE medicoes ADD COLUMN pool_id INTEGER")

    conn.commit()

def _hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt, pwd_hash

def init_db():
    conn = None
    try:
        conn = get_connection()
        _create_schema(conn)
    except Exception as exc:
        print(f"Database initialization failed, retrying with local SQLite: {exc}")
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        conn = sqlite3.connect(DB_NAME)
        _create_schema(conn)
    finally:
        if conn is not None:
            conn.close()

def create_user(username, password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        salt, pwd_hash = _hash_password(password)
        cursor.execute('INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)', (username, salt, pwd_hash))
        conn.commit()
        user_id = cursor.lastrowid
        if not user_id:
            cursor.execute('SELECT last_insert_rowid()')
            user_id = cursor.fetchone()[0]
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        return None # Username already exists

def verify_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, salt, password_hash FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        user_id, salt, stored_hash = row
        _, pwd_hash = _hash_password(password, salt)
        if pwd_hash == stored_hash:
            return user_id
    return None

def create_pool(user_id, name, volume):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO pools (user_id, name, volume) VALUES (?, ?, ?)', (user_id, name, volume))
    conn.commit()
    pool_id = cursor.lastrowid
    if not pool_id:
        cursor.execute('SELECT last_insert_rowid()')
        pool_id = cursor.fetchone()[0]
    conn.close()
    return pool_id

def get_pools(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, volume FROM pools WHERE user_id = ?', (user_id,))
    pools = cursor.fetchall()
    conn.close()
    return [{'id': p[0], 'name': p[1], 'volume': p[2]} for p in pools]

def salvar_medicao(pool_id, responsavel, ph, cloro, generator_level, alcalinidade, dureza, salinidade):
    conn = get_connection()
    cursor = conn.cursor()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO medicoes (pool_id, data_hora, responsavel, ph, cloro, generator_level, alcalinidade, dureza, salinidade )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (pool_id, data_hora, responsavel, ph, cloro, generator_level, alcalinidade, dureza, salinidade))
    conn.commit()
    conn.close()

def ler_historico(pool_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, data_hora, responsavel, ph, cloro, generator_level, alcalinidade, dureza, salinidade FROM medicoes WHERE pool_id = ? ORDER BY data_hora DESC', (pool_id,))
    dados = cursor.fetchall()
    conn.close()
    return dados

def atualizar_medicao(id, data_hora, responsavel, ph, cloro, generator_level, alcalinidade, dureza, salinidade):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE medicoes 
        SET data_hora = ?, responsavel = ?, ph = ?, cloro = ?, generator_level = ?, alcalinidade = ?, dureza = ?, salinidade = ?
        WHERE id = ?
    ''', (data_hora, responsavel, ph, cloro, generator_level, alcalinidade, dureza, salinidade, id))
    conn.commit()
    conn.close()

def deletar_medicao(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM medicoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()

def verify_password_by_id(user_id, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT salt, password_hash FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        salt, stored_hash = row
        _, pwd_hash = _hash_password(password, salt)
        return pwd_hash == stored_hash
    return False

def deletar_piscina(pool_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM medicoes WHERE pool_id = ?', (pool_id,))
    cursor.execute('DELETE FROM pools WHERE id = ?', (pool_id,))
    conn.commit()
    conn.close()
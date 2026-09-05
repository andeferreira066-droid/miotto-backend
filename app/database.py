"""
Banco de dados: SQLite puro (biblioteca padrão do Python — sqlite3),
sem ORM. Para o tamanho deste projeto isso é suficiente e evita mais
uma dependência externa (SQLAlchemy) só pra fazer INSERT/SELECT simples.

Se um dia o projeto crescer bastante (múltiplas equipes grandes, muita
escrita simultânea), trocar para PostgreSQL + SQLAlchemy é o caminho —
a camada crud.py foi escrita isolada exatamente para facilitar essa
troca no futuro sem mexer no resto do backend.

IMPORTANTE sobre o schema de "projetos": a coluna `dados_json` guarda
o objeto inteiro do projeto (imovel, pontos, etc.) exatamente como ele
já existe hoje no localStorage do app.js — para não recriar/duplicar a
estrutura de dados que já funciona no frontend. O backend não recalcula
nada (área, perímetro, azimute...); ele só guarda e devolve o que o
frontend já calculou e enviou, com a mesma lógica de hoje.
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

DB_PATH = os.environ.get("MIOTTO_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "miotto.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                criado_em INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projetos (
                id TEXT PRIMARY KEY,
                usuario_id TEXT NOT NULL,
                nome TEXT NOT NULL,
                dados_json TEXT NOT NULL,
                criado_em INTEGER NOT NULL,
                atualizado_em INTEGER NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projetos_usuario ON projetos(usuario_id)")


def row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def projeto_row_to_public(row: sqlite3.Row) -> dict:
    """Converte uma linha da tabela projetos para o formato que o
    frontend espera (mesmo shape que já existe no localStorage)."""
    dados = json.loads(row["dados_json"])
    dados["id"] = row["id"]
    dados["nome"] = row["nome"]
    dados["criadoEm"] = row["criado_em"]
    dados["atualizadoEm"] = row["atualizado_em"]
    return dados

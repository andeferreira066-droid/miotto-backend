"""Operações de banco de dados para usuários e projetos."""
import json
import time
import uuid
from typing import Optional

from app.database import get_conn, projeto_row_to_public
from app.security import hash_password, verify_password


class EmailJaCadastradoError(Exception):
    pass


class CredenciaisInvalidasError(Exception):
    pass


# --------------------------- Usuários ---------------------------

def criar_usuario(email: str, senha: str) -> dict:
    email = email.strip().lower()
    with get_conn() as conn:
        existente = conn.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone()
        if existente:
            raise EmailJaCadastradoError(f"E-mail {email} já cadastrado")
        user_id = "u_" + uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO usuarios (id, email, senha_hash, criado_em) VALUES (?, ?, ?, ?)",
            (user_id, email, hash_password(senha), int(time.time())),
        )
        return {"id": user_id, "email": email}


def autenticar_usuario(email: str, senha: str) -> dict:
    email = email.strip().lower()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        if not row or not verify_password(senha, row["senha_hash"]):
            raise CredenciaisInvalidasError("E-mail ou senha incorretos")
        return {"id": row["id"], "email": row["email"]}


def buscar_usuario_por_id(user_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT id, email FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        return {"id": row["id"], "email": row["email"]} if row else None


# --------------------------- Projetos ---------------------------

def listar_projetos(usuario_id: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM projetos WHERE usuario_id = ? ORDER BY atualizado_em DESC",
            (usuario_id,),
        ).fetchall()
        return [projeto_row_to_public(r) for r in rows]


def buscar_projeto(usuario_id: str, projeto_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM projetos WHERE usuario_id = ? AND id = ?",
            (usuario_id, projeto_id),
        ).fetchone()
        return projeto_row_to_public(row) if row else None


def salvar_projeto(usuario_id: str, projeto_id: str, nome: str, dados: dict) -> dict:
    """Upsert: cria se não existir, atualiza se já existir. O `id` vem do
    frontend (gerado lá, ex.: "p_1234567890") — o backend não troca esse id,
    só espelha o que o app.js já usa localmente."""
    agora = int(time.time())
    dados_sem_meta = {k: v for k, v in dados.items() if k not in ("id", "nome", "criadoEm", "atualizadoEm")}
    with get_conn() as conn:
        existente = conn.execute(
            "SELECT criado_em FROM projetos WHERE id = ? AND usuario_id = ?",
            (projeto_id, usuario_id),
        ).fetchone()
        criado_em = existente["criado_em"] if existente else agora
        conn.execute(
            """INSERT INTO projetos (id, usuario_id, nome, dados_json, criado_em, atualizado_em)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 nome = excluded.nome,
                 dados_json = excluded.dados_json,
                 atualizado_em = excluded.atualizado_em
               WHERE usuario_id = excluded.usuario_id""",
            (projeto_id, usuario_id, nome, json.dumps(dados_sem_meta), criado_em, agora),
        )
        row = conn.execute("SELECT * FROM projetos WHERE id = ?", (projeto_id,)).fetchone()
        return projeto_row_to_public(row)


def excluir_projeto(usuario_id: str, projeto_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM projetos WHERE id = ? AND usuario_id = ?",
            (projeto_id, usuario_id),
        )
        return cur.rowcount > 0

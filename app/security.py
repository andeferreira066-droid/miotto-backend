"""
Segurança: hash de senha e tokens de acesso (JWT).

Escolhas de projeto (documentadas para quem for manter isso depois):
- Hash de senha com hashlib.pbkdf2_hmac (biblioteca padrão do Python).
  Optamos por isso em vez de bcrypt/passlib para não depender de uma lib
  externa com binário compilado (bcrypt costuma dar dor de cabeça em
  deploys simples tipo Render/Railway). PBKDF2-SHA256 com 260.000
  iterações é o mesmo nível de segurança que o próprio Django usa por
  padrão.
- Token com PyJWT (HS256). Simples, sem estado no servidor (não precisa
  de tabela de sessões) — o token carrega o id do usuário e expira
  sozinho.
"""
import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

import jwt  # PyJWT

# ---------------------------------------------------------------------------
# Chave secreta do JWT — em produção, DEFINA a variável de ambiente
# MIOTTO_SECRET_KEY (ex.: no painel do Render/Railway). Se não for
# definida, geramos uma aleatória só para não travar o "rodar local",
# mas isso invalida todos os tokens a cada reinício do processo.
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("MIOTTO_SECRET_KEY") or secrets.token_hex(32)
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRA_MINUTOS = int(os.environ.get("MIOTTO_TOKEN_EXPIRA_MINUTOS", "43200"))  # 30 dias

PBKDF2_ITERACOES = 260_000


def hash_password(senha: str) -> str:
    """Gera um hash seguro da senha no formato: pbkdf2_sha256$iteracoes$salt$hash"""
    salt = secrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERACOES)
    return f"pbkdf2_sha256${PBKDF2_ITERACOES}${salt}${hash_bytes.hex()}"


def verify_password(senha: str, hash_armazenado: str) -> bool:
    """Confere a senha contra o hash salvo, em tempo constante."""
    try:
        algoritmo, iteracoes_str, salt, hash_hex = hash_armazenado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        iteracoes = int(iteracoes_str)
        novo_hash = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), iteracoes)
        return hmac.compare_digest(novo_hash.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def create_access_token(user_id: str, email: str) -> str:
    agora = int(time.time())
    payload = {
        "sub": user_id,
        "email": email,
        "iat": agora,
        "exp": agora + TOKEN_EXPIRA_MINUTOS * 60,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

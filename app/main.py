"""
Backend do M.I.O.T.T.O — API para sincronizar projetos entre
dispositivos, com autenticação e dados isolados por usuário.

Rodar localmente:
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Depois abra http://localhost:8000/docs para testar a API interativamente
(documentação gerada automaticamente pelo FastAPI).

IMPORTANTE: este backend é ADITIVO. O app continua funcionando 100%
offline com localStorage como hoje — o backend só existe para quem
quiser sincronizar entre aparelhos / ter backup em nuvem / logar com
conta. Nenhum cálculo (área, perímetro, azimute, memorial) foi movido
pra cá: isso continua sendo feito no app.js, como já funcionava.
"""
import os

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app import crud
from app.database import init_db
from app.schemas import (
    LoginRequest,
    ProjetoUpsertRequest,
    RegistroRequest,
    TokenResponse,
)
from app.security import create_access_token, decode_access_token

app = FastAPI(
    title="M.I.O.T.T.O API",
    description="API de sincronização de projetos de levantamento topográfico / terraplanagem.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS: em produção, troque "*" pela URL exata onde o PWA está hospedado
# (ex.: https://miotto.suaempresa.com.br). Deixamos "*" liberado aqui só
# pra facilitar o desenvolvimento local.
# ---------------------------------------------------------------------------
ORIGENS_PERMITIDAS = os.environ.get("MIOTTO_CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_PERMITIDAS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


# --------------------------- Autenticação ---------------------------

def usuario_atual(authorization: str = Header(default=None)) -> dict:
    """Extrai e valida o token JWT do header Authorization: Bearer <token>."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token ausente. Faça login novamente.")
    token = authorization.removeprefix("Bearer ").strip()
    dados = decode_access_token(token)
    if not dados:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido ou expirado. Faça login novamente.")
    usuario = crud.buscar_usuario_por_id(dados["sub"])
    if not usuario:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado.")
    return usuario


@app.get("/health")
def health():
    return {"status": "ok", "app": "miotto-backend"}


@app.post("/auth/registrar", response_model=TokenResponse)
def registrar(body: RegistroRequest):
    try:
        usuario = crud.criar_usuario(body.email, body.senha)
    except crud.EmailJaCadastradoError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já tem uma conta. Tente fazer login.")
    token = create_access_token(usuario["id"], usuario["email"])
    return TokenResponse(access_token=token, usuario=usuario)


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    try:
        usuario = crud.autenticar_usuario(body.email, body.senha)
    except crud.CredenciaisInvalidasError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")
    token = create_access_token(usuario["id"], usuario["email"])
    return TokenResponse(access_token=token, usuario=usuario)


@app.get("/auth/me")
def me(usuario: dict = Depends(usuario_atual)):
    return usuario


# --------------------------- Projetos ---------------------------

@app.get("/projetos")
def listar_projetos(usuario: dict = Depends(usuario_atual)):
    return crud.listar_projetos(usuario["id"])


@app.get("/projetos/{projeto_id}")
def obter_projeto(projeto_id: str, usuario: dict = Depends(usuario_atual)):
    projeto = crud.buscar_projeto(usuario["id"], projeto_id)
    if not projeto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto não encontrado.")
    return projeto


@app.put("/projetos/{projeto_id}")
def salvar_projeto(projeto_id: str, body: ProjetoUpsertRequest, usuario: dict = Depends(usuario_atual)):
    """Cria ou atualiza (upsert). O id do projeto é o mesmo já usado no
    localStorage do frontend — o backend não gera outro id."""
    if body.id != projeto_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "id do corpo da requisição não bate com o da URL.")
    dados = body.dict()
    return crud.salvar_projeto(usuario["id"], projeto_id, body.nome, dados)


@app.delete("/projetos/{projeto_id}")
def excluir_projeto(projeto_id: str, usuario: dict = Depends(usuario_atual)):
    ok = crud.excluir_projeto(usuario["id"], projeto_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto não encontrado.")
    return {"excluido": True}

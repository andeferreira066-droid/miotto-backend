from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class RegistroRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=6, description="Mínimo de 6 caracteres")


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: dict


class ProjetoUpsertRequest(BaseModel):
    """Espelha o objeto de projeto que já existe no localStorage do app.js:
    { id, nome, imovel, pontos, ... }. Campos extras que o frontend mandar
    são aceitos e guardados como estão (não recalculamos nada aqui)."""
    id: str
    nome: str
    imovel: Optional[dict] = None
    pontos: Optional[list] = None

    class Config:
        extra = "allow"


class ProjetoResponse(BaseModel):
    id: str
    nome: str
    criadoEm: int
    atualizadoEm: int

    class Config:
        extra = "allow"

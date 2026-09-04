"""
Teste de ponta a ponta da API, usando o TestClient do FastAPI (não sobe
servidor de verdade, chama a aplicação em memória — rápido e não precisa
de porta livre).

Rodar (depois de instalar as dependências):
    pip install -r requirements.txt
    python3 test_api.py

Isso NÃO foi possível rodar no ambiente onde este código foi gerado
(sandbox sem acesso à internet para instalar o FastAPI), então rode
localmente antes de colocar em produção. Os módulos de lógica pura
(app/security.py e app/crud.py) já foram testados e confirmados
funcionando à parte — este script testa a "cola" HTTP por cima deles.
"""
import os

os.environ["MIOTTO_DB_PATH"] = "./teste_e2e.db"
if os.path.exists("./teste_e2e.db"):
    os.remove("./teste_e2e.db")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def esperar(cond, msg):
    if not cond:
        raise AssertionError("FALHOU: " + msg)
    print("OK:", msg)


# 1. Health check
r = client.get("/health")
esperar(r.status_code == 200, "GET /health responde 200")

# 2. Registro
r = client.post("/auth/registrar", json={"email": "djovani@miotto.com", "senha": "senha123456"})
esperar(r.status_code == 200, "registro cria usuário")
token = r.json()["access_token"]

# 2b. Registro duplicado deve falhar
r = client.post("/auth/registrar", json={"email": "djovani@miotto.com", "senha": "outra123456"})
esperar(r.status_code == 409, "registro com e-mail duplicado retorna 409")

# 3. Login errado
r = client.post("/auth/login", json={"email": "djovani@miotto.com", "senha": "errada"})
esperar(r.status_code == 401, "login com senha errada retorna 401")

# 4. Login certo
r = client.post("/auth/login", json={"email": "djovani@miotto.com", "senha": "senha123456"})
esperar(r.status_code == 200, "login correto retorna 200")
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 5. Acessar rota protegida sem token
r = client.get("/projetos")
esperar(r.status_code == 401, "GET /projetos sem token retorna 401")

# 6. Criar projeto
projeto = {
    "id": "p_teste_1",
    "nome": "Fazenda Teste",
    "imovel": {"nome": "Fazenda Teste", "resp": "Djovani", "fuso": 23, "hem": "sul"},
    "pontos": [{"nome": "P1", "e": 100, "n": 200, "z": 5}],
}
r = client.put("/projetos/p_teste_1", json=projeto, headers=headers)
esperar(r.status_code == 200, "PUT /projetos cria projeto novo")
esperar(r.json()["nome"] == "Fazenda Teste", "projeto salvo com nome correto")

# 7. Listar
r = client.get("/projetos", headers=headers)
esperar(r.status_code == 200 and len(r.json()) == 1, "GET /projetos lista o projeto criado")

# 8. Atualizar (upsert)
projeto["pontos"].append({"nome": "P2", "e": 150, "n": 200, "z": 6})
r = client.put("/projetos/p_teste_1", json=projeto, headers=headers)
esperar(len(r.json()["pontos"]) == 2, "upsert atualiza pontos do projeto existente")

# 9. Outro usuário não vê o projeto
client.post("/auth/registrar", json={"email": "outra@pessoa.com", "senha": "senha123456"})
r2 = client.post("/auth/login", json={"email": "outra@pessoa.com", "senha": "senha123456"})
headers2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
r = client.get("/projetos", headers=headers2)
esperar(r.status_code == 200 and len(r.json()) == 0, "isolamento entre usuários (outro usuário não vê o projeto)")

# 10. Excluir
r = client.delete("/projetos/p_teste_1", headers=headers)
esperar(r.status_code == 200, "DELETE /projetos exclui o projeto")
r = client.get("/projetos/p_teste_1", headers=headers)
esperar(r.status_code == 404, "projeto excluído retorna 404 ao buscar")

os.remove("./teste_e2e.db")
print("\nTODOS OS TESTES DE API PASSARAM")

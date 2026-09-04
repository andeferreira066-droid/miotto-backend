# M.I.O.T.T.O — Backend

API para sincronizar os projetos do app entre aparelhos, com login e
dados isolados por usuário. **O app continua funcionando 100% offline
sem isso** — este backend é uma camada opcional a mais em cima do que
já existe (localStorage continua sendo a fonte de dados no dia a dia).

## O que ele faz

- Cadastro/login por e-mail e senha (senha nunca é salva em texto puro — hash PBKDF2-SHA256)
- Token de sessão (JWT), válido por 30 dias por padrão
- Salvar, listar, buscar e excluir projetos — cada usuário só vê os próprios
- **Não recalcula nada**: área, perímetro, azimute, memorial etc. continuam sendo calculados no `app.js`, exatamente como hoje. O backend só guarda e devolve o JSON do projeto.

## Rodando localmente

```bash
cd miotto-backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # e ajuste MIOTTO_SECRET_KEY
export $(cat .env | xargs)      # Windows: defina as variáveis manualmente

uvicorn app.main:app --reload --port 8000
```

Abra **http://localhost:8000/docs** — o FastAPI gera uma tela interativa
onde dá pra testar cada rota (registrar, logar, criar projeto...) direto
no navegador, sem precisar de Postman.

## Rodando os testes

```bash
python3 test_api.py
```

> Nota: este backend foi escrito e teve sua lógica de negócio
> (senha/token em `app/security.py` e banco de dados em `app/crud.py`)
> testada de verdade durante o desenvolvimento. O teste de ponta a
> ponta acima (`test_api.py`, camada HTTP/FastAPI) não pôde ser
> executado no ambiente onde este código foi gerado por falta de
> acesso à internet para instalar o FastAPI — rode-o localmente antes
> de colocar em produção, é rápido (menos de 1 segundo).

## Rotas

| Método | Rota                | Autenticado? | O que faz |
|--------|----------------------|:---:|---|
| GET    | `/health`            | não | ping de status |
| POST   | `/auth/registrar`    | não | cria conta, devolve token |
| POST   | `/auth/login`        | não | login, devolve token |
| GET    | `/auth/me`           | sim | dados do usuário logado |
| GET    | `/projetos`          | sim | lista projetos do usuário |
| GET    | `/projetos/{id}`     | sim | busca um projeto |
| PUT    | `/projetos/{id}`     | sim | cria ou atualiza (upsert) |
| DELETE | `/projetos/{id}`     | sim | exclui |

Autenticação: header `Authorization: Bearer <token>`.

## Colocando no ar (deploy gratuito para começar)

**Render** ou **Railway** são as opções mais simples para um backend
Python pequeno como esse:

1. Suba esta pasta `miotto-backend` num repositório Git
2. Crie um novo "Web Service" apontando pro repo
3. Comando de start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Configure as variáveis de ambiente do `.env.example` no painel (principalmente `MIOTTO_SECRET_KEY` e `MIOTTO_CORS_ORIGINS` com a URL onde o PWA vai ficar hospedado)

Depois, no frontend, é só trocar `MIOTTO_API_URL` em `app.js` pela URL
pública que o Render/Railway te der (ex.: `https://miotto-backend.onrender.com`).

## Próximos passos sugeridos (não implementados ainda)

- Recuperação de senha por e-mail
- Rate limiting no login (evitar força bruta)
- Trocar SQLite por PostgreSQL se o uso crescer (a camada `crud.py` foi isolada pra facilitar essa troca)
- Compartilhamento de projeto entre usuários de uma mesma equipe

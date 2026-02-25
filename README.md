# Integração Microsoft Teams + Databricks Genie (Azure) — Guia de Implementação (Manual)

Este guia explica como publicar um bot no **Microsoft Teams** que encaminha perguntas para o **Databricks Genie** (Azure Databricks), usando:

- **Azure Bot Service** (canal Teams)
- Runtime do endpoint do bot (escolha 1): **Azure Functions (Python)**
- Runtime do endpoint do bot (escolha 2): **Azure Container Apps (container + FastAPI)**
- **Microsoft Entra ID (Azure AD)** para autenticação (Service Principal / OAuth)

A base do código está na raiz deste repositório.

---

## Estrutura do projeto

```
./
├── function_app.py             # Entrypoint — Azure Functions
├── config.py                   # Variáveis de ambiente
├── config.env                  # Template .env
├── requirements.txt            # Dependências Python (Functions)
├── host.json                   # Config Azure Functions
├── install.sh                  # Script de instalação automatizada (Azure CLI)
├── bot/                        # Lógica do bot (Teams)
│   ├── __init__.py
│   └── teams_bot.py
├── databricks/                 # Cliente Genie (API + OAuth)
│   ├── __init__.py
│   └── genie_client.py
├── containerapp/               # Entrypoint alternativo — Azure Container Apps
│   ├── __init__.py
│   ├── app.py                  # FastAPI server
│   ├── Dockerfile
│   └── requirements.txt
├── teams-app-package/          # Manifesto e ícones do Teams
│   ├── manifest.json
│   ├── color.png
│   └── outline.png
├── scripts/                    # Scripts auxiliares
│   └── create_deployment_linux.sh
└── docs/                       # Credenciais geradas pelo install.sh
```

---

## 1) Visão geral (arquitetura)

Fluxo:

1. Usuário envia mensagem no **Teams**
2. O **Teams** entrega a atividade para o **Azure Bot Service**
3. O Bot Service chama o endpoint do bot (via HTTPS) em **Azure Functions** *ou* **Azure Container Apps**
4. O serviço obtém um token do Entra ID (client credentials) e chama a **API do Databricks Genie**
5. O serviço devolve a resposta ao Teams

Endpoints expostos pelo serviço:

- `POST /api/messages` (webhook do Bot Framework)
- `GET /api/health` (health check)

---

## 2) Pré‑requisitos

### Azure / Entra
- Assinatura Azure e permissão para criar:
  - Resource Group
  - **Azure Bot** (Bot Service / Bot Channels Registration)
  - Runtime do endpoint (um dos dois):
    - **Function App** (Linux, Python) + Storage Account
    - **Container App** (+, tipicamente, um registry como ACR)
- Permissão no **Entra ID** para criar **App Registration** e **Client Secret**.

### Teams
- Permissão (ou time de TI) para permitir **upload de aplicativo customizado** (Teams Admin Center) e publicar um app interno.

### Azure Databricks / Genie
- Workspace **Azure Databricks** (tipicamente Premium) com **Genie** habilitado.
- Um **Genie Space** existente e o **Space ID**.
- Permissão de admin (ou suporte do admin) para:
  - Adicionar **Service Principal** no workspace
  - Conceder acesso ao **Genie Space**

---

## 3) Variáveis de ambiente necessárias (Functions ou Container Apps)

O bot lê configurações via variáveis de ambiente (ver `config.py`). Configure no runtime escolhido:
- **Azure Functions**: Function App → *Configuration / Environment variables*
- **Azure Container Apps**: Container App → *Containers → Environment variables / Secrets*

### Databricks (Service Principal)
- `DATABRICKS_HOST` — URL do workspace (ex.: `https://adb-<id>.<n>.azuredatabricks.net`)
- `DATABRICKS_GENIE_SPACE_ID` — ID do Genie Space
- `DATABRICKS_TENANT_ID` — Tenant ID do Entra
- `DATABRICKS_CLIENT_ID` — Application (client) ID do app no Entra
- `DATABRICKS_CLIENT_SECRET` — Client secret

### Bot Framework / Teams
- `MICROSOFT_APP_ID` — mesmo App (client) ID
- `MICROSOFT_APP_PASSWORD` — mesmo client secret
- `MICROSOFT_APP_TENANT_ID` — Tenant ID (recomendado para apps single-tenant)

### Opcional
- `LOG_LEVEL` — ex.: `INFO`

Observação: este projeto usa **um único App Registration** tanto para o Bot Framework quanto para autenticar no Databricks.

---

## 4) Implementação manual (Portal) — passo a passo

### Passo 1 — Criar App Registration (Entra ID)

1. Acesse **Entra admin center** → **App registrations** → **New registration**
2. Nome sugerido: `databricks-genie-teams-bot-<cliente>`
3. *Supported account types*: **Single tenant**
4. Após criar, anote:
   - **Application (client) ID**  → será `MICROSOFT_APP_ID` e `DATABRICKS_CLIENT_ID`
   - **Directory (tenant) ID** → será `MICROSOFT_APP_TENANT_ID` e `DATABRICKS_TENANT_ID`

#### Criar Client Secret
1. Em **Certificates & secrets** → **New client secret**
2. Copie o valor do secret (uma vez só) → será `MICROSOFT_APP_PASSWORD` e `DATABRICKS_CLIENT_SECRET`

#### Permissão de API para Azure Databricks
1. Em **API permissions** → **Add a permission**
2. Selecione **APIs my organization uses** (ou Microsoft APIs) e procure por **Azure Databricks**
3. Adicione a permissão `user_impersonation`
4. Clique em **Grant admin consent** (pode exigir um admin)

> Se não houver consentimento/admin, o bot tende a falhar com 401 ao chamar o Databricks.

---

### Passo 2 — Criar a Function App (Azure Functions)

1. Azure Portal → **Create a resource** → **Function App**
2. Selecione:
   - Publish: **Code**
   - Runtime stack: **Python**
   - Version: **3.11**
   - Operating System: **Linux**
   - Plan type: **Consumption** (ou outro, conforme governança)
3. Conclua a criação.

#### Configurar variáveis de ambiente
1. Function App → **Settings → Environment variables** (ou **Configuration → Application settings**)
2. Adicione todas as chaves da seção **3)**.
3. Adicione também (recomendado para dependências):
   - `PYTHON_ISOLATE_WORKER_DEPENDENCIES=1`
   - `PYTHON_ENABLE_WORKER_EXTENSIONS=1`
   - `FUNCTIONS_WORKER_RUNTIME=python`

---

### Passo 3 — Publicar o código na Function App

Você precisa publicar o conteúdo deste repositório (incluindo dependências Python) para rodar em Linux.

Opção recomendada (mais simples): **Zip Push Deploy via Kudu**

1. Gere um pacote `.zip` com as dependências Linux.
   - O repositório traz o script: `scripts/create_deployment_linux.sh`
   - Em Windows, execute via **WSL2** ou **Azure Cloud Shell**.
   - O script gera: `databricks-genie-bot-deploy-linux.zip`
2. Acesse o Kudu:
   - `https://<NOME-DA-FUNCTION-APP>.scm.azurewebsites.net`
3. Vá em **Tools → Zip Push Deploy** e faça upload do `.zip`.
4. Valide:
   - `https://<HOST-DA-FUNCTION-APP>/api/health` retorna `{"status":"healthy"...}`

---

### Passo 4 — Criar o Azure Bot e apontar para a Function

1. Azure Portal → **Create a resource** → procure por **Azure Bot** (ou **Bot Channels Registration**)
2. Durante a criação/configuração:
   - **Messaging endpoint**: `https://<HOST-DA-FUNCTION-APP>/api/messages`
   - **Microsoft App ID**: o `Application (client) ID` do Passo 1
   - **Microsoft App password**: o client secret
3. Após criado, habilite o canal **Microsoft Teams**.

---

### Passo 5 — Configurar Databricks (Service Principal) e permissões do Genie Space

1. Acesse o workspace do Databricks
2. **Settings → Admin Console → Identity and access → Service principals**
3. **Add service principal** usando o **Application (client) ID** do seu App Registration
4. Garanta o entitlement **Workspace access**

#### Conceder acesso ao Genie Space
1. Abra o Genie Space
2. Clique em **Share**
3. Adicione o service principal e conceda **Can use**

---

### Passo 6 — Criar o pacote do app do Teams (manifest) e fazer upload

O Teams precisa de um *app package* (ZIP) contendo `manifest.json` e ícones.

1. Edite `teams-app-package/manifest.json`:
   - `id`: coloque o **Microsoft App ID**
   - `bots[0].botId`: coloque o **Microsoft App ID**
   - `validDomains`: inclua o domínio do seu Function App (ex.: `seuapp.azurewebsites.net`)
2. Crie o zip contendo:
   - `manifest.json`
   - `color.png`
   - `outline.png`
3. Faça upload no **Teams Admin Center** (ou no cliente Teams, se permitido):
   - Apps → Manage apps → Upload
4. Adicione o bot a um chat (1:1) ou a um canal.

---

## 4B) Implementação manual (Portal) — Azure Container Apps

Este cenário substitui apenas o **runtime** do endpoint (em vez de Functions, roda em Container Apps). O **Azure Bot Service** continua sendo o ponto de integração com o Teams, e o *Messaging endpoint* permanece `https://<host>/api/messages`.

### Passo B1 — Preparar o código/artefatos

Este repositório já inclui um entrypoint alternativo para Container Apps em:

- `containerapp/app.py` (FastAPI)
- `containerapp/Dockerfile`
- `containerapp/requirements.txt`

Endpoints expostos pelo container:
- `POST /api/messages`
- `GET /api/health`

### Passo B2 — Build e push da imagem (ACR)

O Dockerfile está em `containerapp/Dockerfile` e o build deve ser executado a partir da **raiz do repositório**:

```bash
# Build local (para teste)
docker build -f containerapp/Dockerfile -t genie-teams-bot .

# Build + push direto no ACR (recomendado)
az acr build --registry <NOME-DO-ACR> --image genie-teams-bot:latest -f containerapp/Dockerfile .
```

### Passo B3 — Criar o Container App

1. Azure Portal → **Container Apps** → **Create**
2. Escolha a imagem publicada
3. Habilite **Ingress = External**
4. Configure o **Target port** para `8000` (o app escuta `PORT`, default 8000)
5. Configure as variáveis de ambiente (seção **3**). Sugestão:
   - Secrets para `DATABRICKS_CLIENT_SECRET` e `MICROSOFT_APP_PASSWORD`

Após criado, valide:
- `GET https://<FQDN-DO-CONTAINER-APP>/api/health`

### Passo B4 — Criar/Configurar o Azure Bot apontando para o Container App

No **Azure Bot** (ou ao criar um novo):
- **Messaging endpoint**: `https://<FQDN-DO-CONTAINER-APP>/api/messages`
- **Microsoft App ID** / secret: os mesmos do App Registration (Passo 1)
- Habilite o canal **Microsoft Teams**

### Passo B5 — Atualizar o manifest do Teams

Em `teams-app-package/manifest.json`:
- `validDomains`: inclua o domínio do Container App (ex.: `*.azurecontainerapps.io` ou o FQDN específico do app)

---

## 5) Testes rápidos

- Health check: `GET https://<host>/api/health`
- No Teams (chat 1:1):
  - `hello`
  - uma pergunta real para o seu Genie Space
- Em canal: mencione o bot, por exemplo:
  - `@Databricks Genie quais são os indicadores X do mês?`

---

## 6) Troubleshooting (erros comuns)

### Bot não responde no Teams
- Verifique se o **Messaging endpoint** no Azure Bot aponta para `/api/messages`.
- Verifique se o app do Teams foi publicado/permitido e se o *upload custom* está habilitado.

### Erro de autenticação do Bot Framework
- Confirme `MICROSOFT_APP_ID` e `MICROSOFT_APP_PASSWORD` (secret) no runtime escolhido (Function App ou Container App).
- Confirme que o Azure Bot está usando o mesmo App ID/secret.

### Erros Databricks/Genie (401/403/404)
- `401 Unauthorized`:
  - secret/tenant/client id incorretos
  - consentimento do **Azure Databricks API permission** não concedido
- `403 Forbidden`:
  - service principal sem acesso ao workspace/Genie Space
- `404 Not Found`:
  - `DATABRICKS_GENIE_SPACE_ID` incorreto

### Logs
- **Functions**: Function App → **Monitoring** → logs / Application Insights.
- **Container Apps**: Container App → **Logs** (Log Analytics), e eventos de revision/deploy.

---

## 7) Boas práticas de segurança

- Armazene `CLIENT_SECRET`/`APP_PASSWORD` no **Azure Key Vault** e referencie no Function App (em vez de colar o secret diretamente).
- Defina política de rotação de segredos.
- Restrinja permissões de quem pode fazer upload de app no Teams.

---

## 8) Referências no código

- Endpoint HTTP (Functions): `function_app.py`
- Endpoint HTTP (Container Apps): `containerapp/app.py`
- Variáveis de ambiente: `config.py`
- Lógica do bot/Teams: `bot/teams_bot.py`
- Cliente Genie + OAuth client_credentials: `databricks/genie_client.py`


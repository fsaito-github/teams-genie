# Databricks Genie — Bot para Microsoft Teams

## O que é este projeto?

Este projeto permite que os usuários da sua organização façam **perguntas sobre dados diretamente no Microsoft Teams**. As perguntas são enviadas para o **Databricks Genie** (uma inteligência artificial do Databricks que entende linguagem natural e consulta seus dados automaticamente), e a resposta volta ao Teams em poucos segundos.

**Exemplo de uso no Teams:**

```
Usuário:  Qual foi o volume de água tratada no último mês?
Bot:      [resposta gerada pelo Genie com tabela de resultados]
```

---

## Como funciona? (visão simplificada)

```
┌──────────────┐       ┌──────────────────┐       ┌─────────────────────┐       ┌──────────────────┐
│  Usuário no  │──────▶│   Azure Bot      │──────▶│  Serviço na nuvem   │──────▶│  Databricks      │
│  Teams       │◀──────│   Service        │◀──────│  (Function App ou   │◀──────│  Genie (IA)      │
│              │       │                  │       │   Container App)    │       │                  │
└──────────────┘       └──────────────────┘       └─────────────────────┘       └──────────────────┘
```

1. O usuário envia uma mensagem no Teams.
2. O **Azure Bot Service** recebe a mensagem e a encaminha para o nosso serviço.
3. O serviço (que pode ser uma **Azure Function** ou um **Azure Container App**) se autentica no Databricks e envia a pergunta para o **Genie**.
4. O Genie processa a pergunta, consulta os dados e devolve a resposta.
5. A resposta aparece no chat do Teams para o usuário.

---

## Escolha o modelo de hospedagem

Este projeto oferece **duas opções** para hospedar o serviço que conecta o Teams ao Genie. Escolha a que melhor se encaixa no seu ambiente:

| | **Opção A — Azure Functions** | **Opção B — Azure Container Apps** |
|---|---|---|
| **Ideal para** | Implantação rápida, sem gerenciar infraestrutura | Maior controle sobre o ambiente de execução |
| **Custo** | Paga apenas pelo uso (consumo) | Paga pelo container em execução |
| **Complexidade** | Menor — deploy via ZIP | Maior — requer build de imagem Docker |
| **Arquivos do repositório** | `function_app.py`, `requirements.txt`, `host.json` | `containerapp/app.py`, `containerapp/Dockerfile`, `containerapp/requirements.txt` |

> **Dica:** se você não tem preferência, recomendamos a **Opção A (Azure Functions)** por ser mais simples.

---

## O que você vai precisar (pré-requisitos)

Antes de começar, confirme que você tem acesso aos seguintes itens:

### Na Azure
- Uma **assinatura Azure** ativa.
- Permissão para criar recursos (Function App ou Container App, Bot Service, Storage Account).
- Acesso ao **Microsoft Entra ID** (antigo Azure AD) para registrar um aplicativo.

### No Teams
- Permissão para **fazer upload de aplicativos personalizados** no Teams (ou apoio do time de TI para isso).

### No Databricks
- Um **workspace Azure Databricks** (plano Premium).
- Um **Genie Space** já criado com acesso aos dados desejados.
- O **ID do Genie Space** (você encontra na URL do Genie Space no Databricks).
- Permissão de administrador para adicionar um Service Principal ao workspace.

---

## Estrutura do repositório

Abaixo estão os arquivos deste repositório e para que cada um serve:

```
./
├── function_app.py                         ← Código principal (Opção A: Azure Functions)
├── config.py                               ← Lê as configurações/variáveis de ambiente
├── config.env                              ← Modelo de configuração (copie para .env)
├── requirements.txt                        ← Lista de dependências Python (Opção A)
├── host.json                               ← Configuração do Azure Functions
├── install.sh                              ← Script que automatiza toda a instalação (Opção A)
│
├── bot/                                    ← Código do bot do Teams
│   ├── __init__.py
│   └── teams_bot.py                        ← Lógica de receber/responder mensagens
│
├── databricks/                             ← Código de conexão com o Databricks Genie
│   ├── __init__.py
│   └── genie_client.py                     ← Autenticação e chamadas à API do Genie
│
├── containerapp/                           ← Código principal (Opção B: Container Apps)
│   ├── __init__.py
│   ├── app.py                              ← Servidor web (FastAPI)
│   ├── Dockerfile                          ← Receita para construir a imagem Docker
│   └── requirements.txt                    ← Lista de dependências Python (Opção B)
│
├── teams-app-package/                      ← Pacote do aplicativo no Teams
│   ├── manifest.json                       ← Definição do bot para o Teams
│   ├── color.png                           ← Ícone colorido do bot
│   └── outline.png                         ← Ícone de contorno do bot
│
├── scripts/                                ← Scripts auxiliares
│   └── create_deployment_linux.sh          ← Gera o pacote .zip para deploy (Opção A)
│
└── docs/                                   ← Pasta para credenciais geradas pelo install.sh
```

---

## Informações que você precisará anotar durante o processo

Ao longo dos passos abaixo, você vai gerar e coletar algumas informações. Recomendamos anotá-las em um local seguro:

| Informação | Onde é gerada | Onde será usada |
|---|---|---|
| **Application (client) ID** | Passo 1 (Entra ID) | Configuração do serviço, Bot Service, Databricks e manifest do Teams |
| **Directory (tenant) ID** | Passo 1 (Entra ID) | Configuração do serviço |
| **Client Secret** | Passo 1 (Entra ID) | Configuração do serviço e Bot Service |
| **URL do serviço** | Passo 2A ou 2B | Bot Service (messaging endpoint) e manifest do Teams |
| **Genie Space ID** | Já existente no Databricks | Configuração do serviço |

> ⚠️ **Importante:** o Client Secret é exibido apenas uma vez. Se você perder, precisará gerar um novo.

---

## Passo 1 — Registrar o aplicativo no Entra ID (identidade)

> **O que é isso?** O Entra ID (antigo Azure AD) é o serviço de identidade da Microsoft. Precisamos registrar nosso bot como um "aplicativo" para que ele possa se autenticar tanto no Teams quanto no Databricks.
>
> 📂 **Arquivos envolvidos:** nenhum — este passo é feito inteiramente no portal.

### 1.1 Criar o registro do aplicativo

1. Acesse o portal [**Entra admin center**](https://entra.microsoft.com).
2. No menu lateral, clique em **Applications** → **App registrations** → **New registration**.
3. Preencha:
   - **Name:** `databricks-genie-teams-bot` (ou o nome que preferir)
   - **Supported account types:** selecione **Accounts in this organizational directory only (Single tenant)**
4. Clique em **Register**.
5. Na tela seguinte, anote:
   - **Application (client) ID** — é um código como `74cf5c8b-6df2-42fb-97b0-61ac5c84ceb6`
   - **Directory (tenant) ID** — também é um código similar

### 1.2 Criar o Client Secret (senha do aplicativo)

1. No menu lateral do aplicativo que você acabou de criar, clique em **Certificates & secrets**.
2. Clique em **New client secret**.
3. Dê uma descrição (ex.: `bot-secret`) e escolha a validade desejada.
4. Clique em **Add**.
5. **Copie imediatamente** o valor do secret (coluna **Value**) — ele só é exibido uma vez.

### 1.3 Dar permissão para acessar o Databricks

1. No menu lateral, clique em **API permissions** → **Add a permission**.
2. Clique na aba **APIs my organization uses**.
3. Pesquise por **Azure Databricks** e selecione.
4. Marque a permissão **user_impersonation** e clique em **Add permissions**.
5. De volta à lista de permissões, clique em **Grant admin consent for [sua organização]**.
   - Se você não for administrador, peça a um administrador para aprovar.

> ⚠️ Sem essa aprovação (admin consent), o bot não conseguirá se conectar ao Databricks e retornará erro 401.

---

## Opção A — Implantação com Azure Functions

> Siga os passos 2A a 4A se você escolheu Azure Functions.

### Passo 2A — Criar a Function App na Azure

> **O que é isso?** A Function App é o serviço na nuvem que vai executar o código do bot. Ela recebe as mensagens do Teams e se comunica com o Databricks Genie.
>
> 📂 **Arquivos envolvidos:**
> - `function_app.py` — código principal que a Function App executa
> - `config.py` — lê as variáveis de ambiente configuradas abaixo
> - `host.json` — configuração interna do Azure Functions
> - `requirements.txt` — lista de bibliotecas Python necessárias

#### Criar o recurso

1. No [Portal Azure](https://portal.azure.com), clique em **Create a resource**.
2. Pesquise por **Function App** e clique em **Create**.
3. Preencha:
   - **Resource Group:** crie um novo ou use um existente (ex.: `databricks-genie-rg`)
   - **Function App name:** escolha um nome único (ex.: `genie-bot-func`)
   - **Publish:** Code
   - **Runtime stack:** Python
   - **Version:** 3.11
   - **Operating System:** Linux
   - **Plan type:** Consumption (serverless)
4. Conclua a criação e aguarde o deploy.

#### Configurar as variáveis de ambiente

1. Abra a Function App recém-criada.
2. No menu lateral, vá em **Settings** → **Environment variables** (ou **Configuration** → **Application settings**).
3. Adicione as seguintes variáveis (clique em **+ Add** para cada uma):

| Nome da variável | Valor | De onde vem |
|---|---|---|
| `DATABRICKS_HOST` | URL do seu workspace (ex.: `https://adb-123456.5.azuredatabricks.net`) | Portal do Databricks |
| `DATABRICKS_GENIE_SPACE_ID` | ID do Genie Space | URL do Genie Space no Databricks |
| `DATABRICKS_TENANT_ID` | Directory (tenant) ID | Passo 1.1 |
| `DATABRICKS_CLIENT_ID` | Application (client) ID | Passo 1.1 |
| `DATABRICKS_CLIENT_SECRET` | Valor do Client Secret | Passo 1.2 |
| `MICROSOFT_APP_ID` | Application (client) ID (mesmo valor) | Passo 1.1 |
| `MICROSOFT_APP_PASSWORD` | Valor do Client Secret (mesmo valor) | Passo 1.2 |
| `MICROSOFT_APP_TENANT_ID` | Directory (tenant) ID (mesmo valor) | Passo 1.1 |
| `PYTHON_ISOLATE_WORKER_DEPENDENCIES` | `1` | Fixo |
| `PYTHON_ENABLE_WORKER_EXTENSIONS` | `1` | Fixo |
| `FUNCTIONS_WORKER_RUNTIME` | `python` | Fixo |
| `LOG_LEVEL` | `INFO` | Fixo (opcional) |
| `GENIE_EXAMPLE_QUESTIONS` | Perguntas-exemplo separadas por `\|` | Opcional — exibidas no card de boas-vindas |

4. Clique em **Save** e confirme.

### Passo 3A — Publicar o código na Function App

> **O que é isso?** Precisamos enviar o código deste repositório (e suas dependências) para a Function App que você criou.
>
> 📂 **Arquivos envolvidos:**
> - `scripts/create_deployment_linux.sh` — script que empacota o código + dependências em um `.zip`
> - Todos os arquivos da raiz (`function_app.py`, `config.py`, `bot/`, `databricks/`, etc.)

#### Gerar o pacote de deploy

1. Abra um terminal Linux (pode ser **WSL2** no Windows ou o **Azure Cloud Shell** no portal).
2. Navegue até a raiz deste repositório.
3. Execute:

```bash
chmod +x scripts/create_deployment_linux.sh
./scripts/create_deployment_linux.sh
```

4. O script gera o arquivo `databricks-genie-bot-deploy-linux.zip`.

#### Fazer o upload do pacote

**Opção mais simples — Kudu (interface web):**

1. No navegador, acesse: `https://<NOME-DA-SUA-FUNCTION-APP>.scm.azurewebsites.net`
2. Vá em **Tools** → **Zip Push Deploy**.
3. Arraste o arquivo `databricks-genie-bot-deploy-linux.zip` para a área indicada.
4. Aguarde a conclusão do deploy.

**Opção via linha de comando (Azure CLI):**

```bash
az functionapp deployment source config-zip \
  --resource-group <SEU-RESOURCE-GROUP> \
  --name <NOME-DA-SUA-FUNCTION-APP> \
  --src databricks-genie-bot-deploy-linux.zip
```

#### Validar o deploy

Abra no navegador: `https://<NOME-DA-SUA-FUNCTION-APP>.azurewebsites.net/api/health`

Você deve ver uma resposta como:

```json
{"status": "healthy", "service": "Databricks Genie Teams Bot"}
```

Se essa página não carregar, revise as variáveis de ambiente e tente reiniciar a Function App.

### Passo 4A — Criar o Azure Bot Service

> **O que é isso?** O Azure Bot Service é o intermediário entre o Teams e a sua Function App. Ele recebe as mensagens do Teams e as encaminha para o endpoint correto.
>
> 📂 **Arquivos envolvidos:** nenhum — este passo é feito no portal.

1. No [Portal Azure](https://portal.azure.com), clique em **Create a resource**.
2. Pesquise por **Azure Bot** e clique em **Create**.
3. Preencha:
   - **Bot handle:** um nome único (ex.: `genie-teams-bot`)
   - **Type of App:** Single Tenant
   - **Creation type:** Use existing app registration
   - **App ID:** o **Application (client) ID** do Passo 1.1
   - **App tenant ID:** o **Directory (tenant) ID** do Passo 1.1
4. Após criado, abra o recurso do Bot.
5. No menu lateral, clique em **Configuration**.
6. Em **Messaging endpoint**, coloque:
   ```
   https://<NOME-DA-SUA-FUNCTION-APP>.azurewebsites.net/api/messages
   ```
7. Em **Microsoft App ID**, confirme que é o mesmo ID do Passo 1.
8. Preencha o **App password** com o Client Secret do Passo 1.2.
9. Clique em **Apply** / **Save**.

#### Habilitar o canal do Teams

1. No menu lateral do Bot, clique em **Channels**.
2. Clique em **Microsoft Teams**.
3. Aceite os termos e clique em **Apply**.

> Agora pule para o **Passo 5** (Configurar o Databricks).

---

## Opção B — Implantação com Azure Container Apps

> Siga os passos 2B a 4B se você escolheu Container Apps.

### Passo 2B — Construir a imagem Docker e enviar para o registro

> **O que é isso?** Container Apps executam "imagens Docker" — pacotes que contêm o código e tudo que ele precisa para rodar. Precisamos construir essa imagem e armazená-la em um registro (Azure Container Registry).
>
> 📂 **Arquivos envolvidos:**
> - `containerapp/Dockerfile` — receita para construir a imagem
> - `containerapp/app.py` — código principal que o container executa
> - `containerapp/requirements.txt` — lista de bibliotecas Python para o container
> - `.dockerignore` — lista de arquivos que NÃO devem ir para a imagem
> - `bot/`, `databricks/`, `config.py` — código compartilhado usado pelo container

#### Criar um Azure Container Registry (se ainda não tiver)

1. No [Portal Azure](https://portal.azure.com), clique em **Create a resource** → pesquise **Container Registry**.
2. Preencha nome, resource group e SKU (Basic é suficiente).
3. Clique em **Create**.

#### Construir e publicar a imagem

No terminal (Azure Cloud Shell ou local com Docker instalado), a partir da raiz deste repositório:

```bash
az acr build \
  --registry <NOME-DO-SEU-REGISTRY> \
  --image genie-teams-bot:latest \
  -f containerapp/Dockerfile .
```

> **Nota:** o ponto (`.`) no final é importante — indica que o contexto de build é a raiz do repositório.

### Passo 3B — Criar o Container App

> **O que é isso?** O Container App é o serviço na nuvem que vai executar a imagem Docker que você acabou de criar.
>
> 📂 **Arquivos envolvidos:** nenhum — este passo é feito no portal (a imagem já contém todo o código).

1. No [Portal Azure](https://portal.azure.com), pesquise por **Container Apps** → **Create**.
2. Preencha:
   - **Resource Group:** o mesmo usado anteriormente
   - **Container App name:** ex.: `genie-teams-bot`
   - **Container Apps Environment:** crie um novo ou use existente
3. Na aba **Container**:
   - **Image source:** Azure Container Registry
   - **Registry / Image / Tag:** selecione a imagem `genie-teams-bot:latest` publicada no passo anterior
4. Na aba **Ingress**:
   - **Ingress:** Enabled
   - **Ingress traffic:** Accepting traffic from anywhere
   - **Target port:** `8000`
5. Conclua a criação.

#### Configurar as variáveis de ambiente

1. Abra o Container App criado.
2. No menu lateral, vá em **Containers** → clique no container → **Environment variables**.
3. Adicione as mesmas variáveis da tabela do Passo 2A (exceto as três variáveis `PYTHON_*` e `FUNCTIONS_*`, que são específicas de Functions).
4. Para `DATABRICKS_CLIENT_SECRET` e `MICROSOFT_APP_PASSWORD`, use **Secrets** do Container App (mais seguro).

#### Validar o deploy

1. No menu lateral do Container App, vá em **Overview**.
2. Copie o **Application Url** (algo como `https://genie-teams-bot.bluemoss-abc123.eastus.azurecontainerapps.io`).
3. Abra no navegador: `<Application Url>/api/health`
4. Você deve ver: `{"status": "healthy", "service": "Databricks Genie Teams Bot"}`

### Passo 4B — Criar o Azure Bot Service

> Mesmo procedimento do Passo 4A, com uma diferença no endpoint.
>
> 📂 **Arquivos envolvidos:** nenhum — este passo é feito no portal.

1. Siga as mesmas instruções do **Passo 4A** acima.
2. Na configuração do **Messaging endpoint**, use a URL do Container App:
   ```
   https://<URL-DO-SEU-CONTAINER-APP>/api/messages
   ```
3. Habilite o canal **Microsoft Teams** da mesma forma.

---

## Passo 5 — Configurar o Databricks (comum às duas opções)

> **O que é isso?** Precisamos dizer ao Databricks que o nosso bot tem permissão para acessar o Genie Space. Fazemos isso registrando o mesmo aplicativo (do Passo 1) como um "Service Principal" dentro do Databricks.
>
> 📂 **Arquivos envolvidos:** nenhum — este passo é feito no portal do Databricks.

### 5.1 Adicionar o Service Principal ao workspace

1. Acesse o seu workspace Databricks (ex.: `https://adb-123456.5.azuredatabricks.net`).
2. No canto superior direito, clique no seu nome → **Settings**.
3. Vá em **Identity and access** → **Service principals**.
4. Clique em **+ Add service principal**.
5. Cole o **Application (client) ID** do Passo 1.1.
6. Clique em **Add**.
7. Na lista, clique no service principal recém-adicionado e habilite **Workspace access**.

### 5.2 Dar acesso ao Genie Space

1. No Databricks, abra o seu **Genie Space**.
2. Clique em **Share** (compartilhar).
3. No campo de busca, procure pelo service principal (usando o Application ID ou nome).
4. Selecione a permissão: **Can use**.
5. Clique em **Save**.

---

## Passo 6 — Configurar e instalar o aplicativo no Teams (comum às duas opções)

> **O que é isso?** Para que o bot apareça no Teams, precisamos criar um "pacote de aplicativo" (um arquivo ZIP) e fazer upload no Teams.
>
> 📂 **Arquivos envolvidos:**
> - `teams-app-package/manifest.json` — definição do bot (você precisará editar este arquivo)
> - `teams-app-package/color.png` — ícone colorido (192×192 px)
> - `teams-app-package/outline.png` — ícone de contorno (32×32 px)

### 6.1 Editar o manifest.json

Abra o arquivo `teams-app-package/manifest.json` em um editor de texto e altere os seguintes campos:

1. **`id`** — substitua pelo **Application (client) ID** do Passo 1.1
2. **`bots[0].botId`** — substitua pelo mesmo **Application (client) ID**
3. **`name.short`** e **`name.full`** — personalize com o nome desejado para o bot
4. **`description.short`** e **`description.full`** — personalize a descrição
5. **`validDomains`** — adicione o domínio do seu serviço:
   - Se usou **Functions**: `seuapp.azurewebsites.net`
   - Se usou **Container Apps**: `seuapp.bluemoss-abc123.eastus.azurecontainerapps.io`

### 6.2 Criar o pacote ZIP

Crie um arquivo ZIP contendo **apenas** estes 3 arquivos (sem subpastas):

- `manifest.json`
- `color.png`
- `outline.png`

> **No Windows:** selecione os 3 arquivos dentro da pasta `teams-app-package`, clique com botão direito → **Enviar para** → **Pasta compactada (zipada)**.

### 6.3 Fazer upload no Teams

**Opção 1 — Via Teams Admin Center (recomendado para organizações):**

1. Acesse [admin.teams.microsoft.com](https://admin.teams.microsoft.com).
2. Vá em **Teams apps** → **Manage apps**.
3. Clique em **Upload new app** → **Upload**.
4. Selecione o ZIP criado.

**Opção 2 — Via cliente do Teams (se permitido pela organização):**

1. No Teams, clique em **Apps** (barra lateral).
2. Clique em **Manage your apps** → **Upload an app**.
3. Selecione **Upload a custom app** e escolha o ZIP.

---

## Passo 7 — Testar o bot

1. No Teams, abra um **chat direto** (1:1) com o bot (pesquise pelo nome que você deu no manifest).
2. Envie: `hello`
   - O bot deve responder com uma mensagem de boas-vindas.
3. Envie uma **pergunta sobre seus dados**, por exemplo:
   - `Qual foi o volume de água tratada no último mês?`
   - `Mostre os indicadores de qualidade da última semana`
4. Em um **canal**, mencione o bot:
   - `@NomeDoBotGenie qual o consumo médio por região?`

> Se o bot não responder, consulte a seção de **Resolução de problemas** abaixo.

---

## Resolução de problemas

### O bot não responde no Teams

- Verifique se o **Messaging endpoint** no Azure Bot Service está correto (deve terminar em `/api/messages`).
- Verifique se o aplicativo do Teams foi aprovado e publicado.
- Teste o health check: acesse `https://<url-do-servico>/api/health` no navegador.

### Erro de autenticação (401)

- Confirme que o **Application (client) ID** e o **Client Secret** estão corretos nas variáveis de ambiente.
- Confirme que o Azure Bot Service usa o mesmo Application ID e Secret.
- Verifique se o **admin consent** foi concedido para a permissão do Azure Databricks (Passo 1.3).

### O bot responde "403 Forbidden" ou "404 Not Found"

- **403:** o Service Principal não tem acesso ao workspace ou ao Genie Space. Revise o Passo 5.
- **404:** o ID do Genie Space está incorreto. Verifique o valor de `DATABRICKS_GENIE_SPACE_ID`.

### Onde ver os logs

- **Azure Functions:** abra a Function App → **Monitoring** → **Log stream** ou **Application Insights**.
- **Container Apps:** abra o Container App → **Monitoring** → **Log stream** ou **Logs**.

---

## Boas práticas de segurança

- **Nunca compartilhe** o Client Secret em e-mails, chats ou documentos. Use um gerenciador de senhas ou o Azure Key Vault.
- Configure uma **política de rotação** do secret (ex.: a cada 6 meses).
- Restrinja quem pode fazer upload de aplicativos personalizados no Teams (via Teams Admin Center).
- Em Container Apps, use **Secrets** do Container App para armazenar valores sensíveis em vez de variáveis de ambiente em texto puro.

---

## Referência rápida — mapa de arquivos

| Arquivo | Para que serve |
|---|---|
| `function_app.py` | Código principal — Opção A (Azure Functions) |
| `containerapp/app.py` | Código principal — Opção B (Container Apps) |
| `containerapp/Dockerfile` | Receita para construir a imagem Docker (Opção B) |
| `config.py` | Lê as variáveis de ambiente (usado por ambas as opções) |
| `config.env` | Modelo de arquivo de configuração |
| `bot/teams_bot.py` | Lógica do bot: recebe mensagens do Teams e envia respostas |
| `databricks/genie_client.py` | Conexão com o Databricks Genie: autenticação e chamadas à API |
| `teams-app-package/manifest.json` | Definição do bot para o Teams (precisa ser editado) |
| `teams-app-package/color.png` | Ícone do bot no Teams (192×192 px) |
| `teams-app-package/outline.png` | Ícone de contorno do bot no Teams (32×32 px) |
| `scripts/create_deployment_linux.sh` | Script que gera o pacote ZIP para deploy (Opção A) |
| `install.sh` | Script que automatiza toda a instalação via Azure CLI (Opção A) |


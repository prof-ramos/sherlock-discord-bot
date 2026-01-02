# Comandos e Permissões

Este documento descreve os comandos expostos pelo bot, seus parâmetros e permissões necessárias.

## /chat

Cria uma thread de conversa e processa o primeiro prompt do usuário.

**Exemplo de uso:**
`/chat message:"Qual o prazo do inquérito policial?" model:gpt-4o temperature:0.7`

**Parâmetros:**

- `message` (str, obrigatório): prompt inicial.
- `model` (opcional, padrão: `gpt-4o-mini`): modelo para a conversa.
- `temperature` (float, opcional, padrão: `1.0`): controla aleatoriedade (0.0 a 1.0).
- `max_tokens` (int, opcional, padrão: `512`): limite de tokens da resposta.

**Permissões:**

- Usuário: `send_messages`, `view_channel`.
- Bot: `send_messages`, `view_channel`, `manage_threads`.

**Exemplos adicionais:**

```bash
# Exemplo 1: Pergunta jurídica com modelo específico
/chat message:"Quais são os requisitos para interposição de recurso especial?" model:anthropic/claude-3-sonnet temperature:0.5

# Exemplo 2: Pergunta curta com configuração padrão
/chat message:"O que é dolo eventual?"

# Exemplo 3: Pergunta complexa com resposta longa
/chat message:"Explique a diferença entre prescrição e decadência no direito civil brasileiro" max_tokens:1024
```

**Valores padrão:**
- `model`: `gpt-4o-mini`
- `temperature`: `1.0`
- `max_tokens`: `512`

## Menções ao bot

Quando o bot é mencionado diretamente em um canal, ele responde no próprio canal. Esse fluxo não
cria thread e usa uma configuração padrão de `ThreadConfig`.

## Mensagens em threads do bot

Mensagens enviadas em threads criadas pelo bot são tratadas como parte da conversa, com histórico
limitado por `MAX_THREAD_MESSAGES` e `OPTIMIZED_HISTORY_LIMIT`.

## Política de Configuração

Comandos de configuração devem ser restritos a administradores. Use
`app_commands.checks.has_permissions(administrator=True)` em comandos slash.

**Exemplo de configuração de permissões:**

```python
@app_commands.command(name="config")
@app_commands.checks.has_permissions(administrator=True)
async def config_command(interaction: discord.Interaction):
    # Lógica de configuração
    pass
```

**Permissões necessárias para o bot funcionar corretamente:**
- `send_messages`: Enviar mensagens em canais
- `view_channel`: Ver canais e threads
- `manage_threads`: Criar e gerenciar threads
- `read_message_history`: Acessar histórico de mensagens
- `use_application_commands`: Usar comandos slash
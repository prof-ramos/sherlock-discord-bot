# 🔍 SherlockRamosBot

### ChatBot inteligente no Discord para auxiliar concurseiros brasileiros com dúvidas jurídicas

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.6+-blue.svg)](https://discordpy.readthedocs.io/)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-API-green.svg)](https://openrouter.ai/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Sobre

O **SherlockRamosBot** é um assistente virtual powered by IA projetado especialmente para
concurseiros brasileiros. Utilizando modelos de linguagem avançados através da API do OpenRouter, o
bot oferece suporte para tirar dúvidas sobre temas jurídicos, legislação, jurisprudência e muito
mais.

## ✨ Principais Características

- 🤖 **Múltiplos Modelos de IA**: Acesso a GPT-4, Claude, Gemini e LLaMA via OpenRouter
- 💬 **Conversas Contextuais**: Mantém histórico da conversa em threads
- 📚 **RAG Jurídico**: Base de conhecimento com legislação e jurisprudência (Busca Vetorial)
- ⚡ **Respostas Rápidas**: Processamento otimizado para respostas ágeis
- 🎯 **Foco Jurídico**: Personalizado para auxiliar em estudos para concursos
- 🔒 **Seguro**: Sistema de moderação integrado
- 🌐 **Multi-servidor**: Pode ser usado em vários servidores Discord simultaneamente

---

## 🚀 Funcionalidades

## Comando Principal: `/chat`

Inicia uma thread pública onde você pode conversar com o bot sobre suas dúvidas jurídicas.

### Parâmetros disponíveis

- `message` (obrigatório): Sua pergunta ou dúvida
- `temperature` (opcional): Controla a criatividade (0.0 a 2.0, padrão: 1.0)
- `max_tokens` (opcional): Limite de tokens na resposta

### Exemplos de uso

```text
/chat message:"Qual a diferença entre crime doloso e culposo?"

/chat message:"Explique o princípio da legalidade no Direito Administrativo" temperature:0.7

/chat message:"Cite 3 súmulas importantes do STF sobre direito constitucional"
```

### Como funciona

1. Use `/chat` para iniciar uma conversa em uma thread pública
2. O bot responderá à sua mensagem inicial
3. Continue fazendo perguntas na mesma thread - o bot lembrará do contexto
4. A thread é encerrada automaticamente quando atingir o limite de mensagens ou tokens
5. Você pode iniciar quantas threads quiser!

---

## 🛠️ Instalação e Configuração

## Pré-requisitos

- Python 3.9 ou superior
- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes rápido)
- Conta no Discord com permissões de desenvolvedor
- Chave de API do OpenRouter ([obtenha aqui](https://openrouter.ai/))

## Passo 1: Clone o Repositório

```bash
git clone https://github.com/prof-ramos/sherlock-discord-bot.git
cd sherlock-discord-bot
```

## Passo 2: Instale as Dependências

```bash
uv sync
```

## Passo 3: Configure as Variáveis de Ambiente

1. Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

1. Edite o arquivo `.env` com suas credenciais:

```env
# Chave da API do OpenRouter (obtenha em: https://openrouter.ai/keys)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxx

# URL Base do OpenRouter (não alterar)
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Token do Bot Discord (obtenha em: https://discord.com/developers/applications)
DISCORD_BOT_TOKEN=seu_token_aqui

# Client ID do Discord
DISCORD_CLIENT_ID=seu_client_id_aqui

# IDs dos servidores permitidos (separe por vírgula)
ALLOWED_SERVER_IDS=123456789,987654321

# Canal de moderação (formato: server_id:channel_id)
SERVER_TO_MODERATION_CHANNEL=123456789:987654321

# Modelo padrão (veja modelos disponíveis abaixo)
DEFAULT_MODEL=openai/gpt-3.5-turbo
```

## Passo 4: Configure seu Bot no Discord

1. Acesse o [Discord Developer Portal](https://discord.com/developers/applications)
2. Clique em "New Application" e dê um nome ao seu bot
3. Vá à aba "Bot" e clique em "Add Bot"
   - Clique em "Reset Token" e copie o token para `DISCORD_BOT_TOKEN`
   - Desative "Public Bot" se não quiser que outros vejam seu bot
   - **IMPORTANTE**: Ative "Message Content Intent" em "Privileged Gateway Intents"
4. Vá à aba "OAuth2" e copie o "Client ID" para `DISCORD_CLIENT_ID`
5. Para obter o ID do servidor:
   - No Discord, clique com botão direito no ícone do servidor
   - Clique em "Copiar ID" e cole em `ALLOWED_SERVER_IDS`

## Passo 5: Execute o Bot

```bash
uv run python -m src.main
```

Você verá uma URL de convite no console. Copie e cole no navegador para adicionar o bot ao seu
servidor!

---

## 🤖 Modelos Disponíveis

O SherlockRamosBot suporta diversos modelos via OpenRouter:

| Modelo                            | Descrição                  | Ideal Para                                |
| --------------------------------- | -------------------------- | ----------------------------------------- |
| `openai/gpt-3.5-turbo`            | Rápido e econômico         | Dúvidas gerais, revisões                  |
| `openai/gpt-4o`                   | Mais inteligente e preciso | Questões complexas, análises profundas    |
| `anthropic/claude-3-opus`         | Excelente raciocínio       | Interpretação de leis, argumentação       |
| `anthropic/claude-3-sonnet`       | Balanceado                 | Uso geral, boa relação custo/benefício    |
| `google/gemini-2.0-flash-exp`     | Rápido e avançado          | Análise de textos longos, respostas ágeis |
| `meta-llama/llama-3-70b-instruct` | Open source potente        | Alternativa econômica                     |

**Como alterar o modelo padrão:** Edite `DEFAULT_MODEL` no arquivo `.env`

---

## ⚙️ Personalização

## Ajustando a Personalidade do Bot

Edite o arquivo `src/config.yaml` para personalizar as instruções e exemplos:

```yaml
name: 'SherlockRamosBot'
instructions: 'Você é um assistente especializado em auxiliar concurseiros brasileiros...'
example_conversations:
  - messages:
      - user: 'User'
        text: 'Explique o princípio da legalidade'
      - user: 'SherlockRamosBot'
        text: 'O princípio da legalidade estabelece que...'
```

## Ajustando Parâmetros de Geração

No comando `/chat`, você pode ajustar:

- **Temperature** (0.0 - 2.0):

  - `0.0-0.5`: Respostas mais objetivas e consistentes
  - `0.6-1.0`: Balanceado (recomendado)
  - `1.1-2.0`: Mais criativo e variado

- **Max Tokens**: Limite de tamanho da resposta
  - Padrão: 1000 tokens (~750 palavras)
  - Máximo recomendado: 2000 tokens

---

## 🔒 Permissões Necessárias

Para funcionar corretamente, o bot precisa das seguintes permissões no Discord:

- ✅ Enviar Mensagens
- ✅ Enviar Mensagens em Threads
- ✅ Criar Threads Públicas
- ✅ Gerenciar Mensagens (para moderação)
- ✅ Gerenciar Threads
- ✅ Ler Histórico de Mensagens
- ✅ Usar Comandos de Aplicação

---

## 📚 Exemplos de Uso para Concurseiros

### Dúvidas de Direito Constitucional

```text
/chat message:"Quais são os direitos e garantias fundamentais previstos no Art. 5º da CF/88?"
```

### Questões de Direito Administrativo

```text
/chat message:"Explique os princípios da Administração Pública (LIMPE)"
```

### Direito Penal

```text
/chat message:"Qual a diferença entre excludentes de ilicitude e excludentes de culpabilidade?"
```

### Preparação para Provas

```text
/chat message:"Me faça 5 questões de múltipla escolha sobre Direito Tributário"
```

### Jurisprudência

```text
/chat message:"Quais as principais súmulas do STJ sobre execução penal?"
```

---

## 🐛 Solução de Problemas

### O bot não responde aos comandos

1. Verifique se o bot tem as permissões necessárias no canal
2. Confirme que "Message Content Intent" está ativado no Developer Portal
3. Verifique se o servidor está na lista `ALLOWED_SERVER_IDS`

### Erro de autenticação da API

1. Confirme que sua chave do OpenRouter está correta
2. Verifique se tem créditos na conta do OpenRouter
3. Confirme que `OPENROUTER_BASE_URL` está configurado corretamente

### Bot fica offline

1. Verifique se o `DISCORD_BOT_TOKEN` está correto
2. Confirme que o bot não foi desativado no Developer Portal
3. Verifique os logs para mensagens de erro

---

## 💰 Custos

O SherlockRamosBot usa a API do OpenRouter, que tem preços variados por modelo:

- **GPT-3.5-turbo**: ~$0.002 por 1K tokens (muito econômico)
- **GPT-4**: ~$0.03-0.06 por 1K tokens
- **Claude-3**: ~$0.015-0.075 por 1K tokens

💡 **Dica**: Comece com `openai/gpt-3.5-turbo` para testes e economizar créditos.

Monitore seu uso em: [OpenRouter Dashboard](https://openrouter.ai/activity)

---

## 🗺️ Roadmap

Funcionalidades planejadas para futuras versões do SherlockRamosBot:

### 🎯 Em Desenvolvimento

### ✅ Implementado (Beta)

#### RAG (Retrieval-Augmented Generation)

- **Objetivo**: Integrar base de conhecimento jurídica vetorizada
- **Benefícios**:
  - 📚 Respostas baseadas em legislação específica armazenada
  - 📖 Doutrinas e materiais de estudo indexados
- **Como usar**:
  - Administradores podem ingerir documentos usando `uv run scripts/ingest_docs.py arquivo.pdf`
  - O bot consultará automaticamente a base ao responder

### 🚀 Próximas Features

#### Sistema de Flashcards Interativos

- Geração automática de flashcards a partir de tópicos estudados
- Revisão espaçada baseada em algoritmo SM-2
- Tracking de progresso por matéria

#### Quiz e Simulados Personalizados

- Geração de questões estilo banca (CESPE, FCC, FGV, etc.)
- Simulados cronometrados
- Análise de desempenho e estatísticas

#### Assistente de Revisão Programada

- Lembretes automáticos de revisão
- Cronograma de estudos personalizado
- Acompanhamento de metas diárias/semanais

#### Integração com Legislação Atualizada

- Sync automático com Planalto/DOU
- Notificações de alterações legislativas importantes
- Comparação de versões de leis (redação antiga vs. nova)

#### Análise de Jurisprudência

- Busca de decisões relevantes do STF/STJ
- Resumos automáticos de julgados
- Tendências jurisprudenciais por tema

#### Sistema de Ranking e Gamificação

- Sistema de pontos por interações
- Badges de conquistas (estudou X dias seguidos, etc.)
- Ranking semanal de estudantes mais ativos

### 💡 Ideias Futuras

- 🎙️ Suporte a comandos de voz
- 📱 App mobile complementar
- 👥 Salas de estudo colaborativas
- 🎬 Integração com vídeo-aulas
- 📊 Dashboard web de estatísticas
- 🔔 Sistema de notificações de editais

### 🤝 Contribua com Ideias

Tem uma sugestão? Abra uma
[Discussion](https://github.com/prof-ramos/sherlock-discord-bot/discussions) ou
[Issue](https://github.com/prof-ramos/sherlock-discord-bot/issues) com a tag `enhancement`!

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Faça um Fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 📞 Suporte

- 🐛 **Bugs**: Abra uma [Issue](https://github.com/prof-ramos/sherlock-discord-bot/issues)
- 💡 **Sugestões**: Abra uma
  [Discussion](https://github.com/prof-ramos/sherlock-discord-bot/discussions)
- 📧 **Contato**: [prof.ramos@exemplo.com]

---

## 🙏 Agradecimentos

- [OpenAI](https://openai.com/) - Modelos GPT
- [Anthropic](https://anthropic.com/) - Modelos Claude
- [OpenRouter](https://openrouter.ai/) - Plataforma unificada de APIs
- [discord.py](https://discordpy.readthedocs.io/) - Biblioteca Discord para Python

---

### Desenvolvido com ❤️ para a comunidade de concurseiros brasileiros

⭐ Se este projeto te ajudou, considere dar uma estrela!

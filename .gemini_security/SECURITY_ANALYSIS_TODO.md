# Checklist de Análise de Segurança

Start Date: 2026-01-02

## Auditoria de Código (Prazo: 2026-02-02, Responsável: Tech Lead)

| Item                                                                           | Owner  | Status | Date Completed | Issue Link | Notes |
| ------------------------------------------------------------------------------ | ------ | ------ | -------------- | ---------- | ----- |
| Revisar implementação de chaves de API e segredos (verificar `.env` vs código) | Dev    | TODO   |                |            |       |
| Verificar se o `.env` está no `.gitignore`                                     | Dev    | TODO   |                |            |       |
| Confirmar que segredos não estão hardcoded                                     | Dev    | TODO   |                |            |       |
| Validar carregamento via `os.getenv`                                           | Dev    | TODO   |                |            |       |
| Verificar sanitização de inputs do usuário no comando `/chat`                  | Dev    | TODO   |                |            |       |
| Implementar validação de comprimento (max chars)                               | Dev    | TODO   |                |            |       |
| Sanitizar caracteres de controle e markdown                                    | Dev    | TODO   |                |            |       |
| Auditar dependências com vuln (executar `uv pip check` ou similar)             | DevOps | TODO   |                |            |       |
| Rodar `uv pip check` / `safety check` no CI                                    | DevOps | TODO   |                |            |       |
| Auditar SQL Injection em queries RAG (verificar queries parametrizadas)        | Dev    | TODO   |                |            |       |
| Validar permissões do arquivo `.env` (chmod 600, owner)                        | DevOps | TODO   |                |            |       |
| Adicionar tasks de CI para Lint/SAST (Bandit, ESLint, Semgrep)                 | DevOps | TODO   |                |            |       |
| Verificar uso de queries parametrizadas em todo o código RAG                   | Dev    | TODO   |                |            |       |
| Validar que todas as queries usam $1, $2, etc. em vez de string formatting     | Dev    | TODO   |                |            |       |
| Auditar uso de asyncpg.execute() com parâmetros separados                      | Dev    | TODO   |                |            |       |
| Garantir que embeddings são passados como arrays, não strings                  | Dev    | TODO   |                |            |       |
| Verificar permissões do arquivo `.env` (deve ser chmod 600, não world-readable) | DevOps | TODO   |                |            |       |
| Adicionar verificação automática de permissões .env no CI                      | DevOps | TODO   |                |            |       |
| Configurar CI para rodar Bandit (Python), Semgrep (multi-lingua) e ESLint      | DevOps | TODO   |                |            |       |
| Commands: uv run bandit -r src/, uv run semgrep --config=auto, npx eslint .    | DevOps | TODO   |                |            |       |
| Agendar execução diária de segurança no CI/CD                                  | DevOps | TODO   |                |            |       |

## Infraestrutura e Deploy (Prazo: 2026-02-09, Responsável: DevOps)

| Item                                                                    | Owner  | Status | Date Completed | Issue Link | Notes |
| ----------------------------------------------------------------------- | ------ | ------ | -------------- | ---------- | ----- |
| Validar permissões do bot no Discord (princípio do menor privilégio)    | DevOps | TODO   |                |            |       |
| Revisar scopes do token (bot, applications.commands)                    | DevOps | TODO   |                |            |       |
| Validar permissões de canal (Send Messages, Read History, View Channel) | DevOps | TODO   |                |            |       |
| Remover permissão de "Administrator" (obrigatório)                      | DevOps | TODO   |                |            |       |
| Configurar logs de auditoria para ações de moderação                    | Dev    | TODO   |                |            |       |
| Criar canal de logs privado para eventos de segurança                   | Dev    | TODO   |                |            |       |
| Revisar regras de firewall/acesso se houver backend exposto             | DevOps | TODO   |                |            |       |
| Verificar segurança Neon/pgvector (RAG)                                 | DevOps | TODO   |                |            |       |
| Garantir conexão SSL/TLS forçada (`sslmode=require`)                    | DevOps | TODO   |                |            |       |
| Validar autenticação (DB user/pass forte)                               | DevOps | TODO   |                |            |       |
| Criptografia de dados em repouso (Neon default encryption)              | DevOps | TODO   |                |            |       |
| Validar permissões específicas: Send Messages, Read Message History     | DevOps | TODO   |                |            |       |
| Verificar intents necessários: GUILD_MEMBERS, GUILD_MESSAGES            | DevOps | TODO   |                |            |       |
| Revisar scopes do token: bot, applications.commands                     | DevOps | TODO   |                |            |       |
| Remover permissão Administrator se presente (obrigatório)               | DevOps | TODO   |                |            |       |
| Documentar permissões mínimas necessárias para operação                  | DevOps | TODO   |                |            |       |

## Privacidade e Dados (Prazo: 2026-02-16, Responsável: DPO/Legal)

| Item                                                                 | Owner   | Status | Date Completed | Issue Link | Notes |
| -------------------------------------------------------------------- | ------- | ------ | -------------- | ---------- | ----- |
| Confirmar quais dados de usuários são persistidos no banco           | DPO     | TODO   |                |            |       |
| Revisar política de retenção de dados da thread                      | Legal   | TODO   |                |            |       |
| Definir TTL para mensagens (ex: 30, 90, 365 dias)                    | Legal   | TODO   |                |            |       |
| Implementar Job de Cleanup automático                                | Dev     | TODO   |                |            |       |
| Documentar conformidade GDPR/LGPD (Right to be forgotten)            | Legal   | TODO   |                |            |       |
| Testes de encenação automatizados para expurgo de dados              | QA      | TODO   |                |            |       |
| Garantir que o RAG não exponha documentos sensíveis não intencionais | Content | TODO   |                |            |       |
| Definir TTL específico: 90 dias para mensagens de thread             | Legal   | TODO   |                |            |       |
| Implementar job de cleanup com TTL de 90 dias                         | Dev     | TODO   |                |            |       |
| Documentar procedimentos GDPR/LGPD para right-to-be-forgotten        | Legal   | TODO   |                |            |       |
| Criar testes automatizados para verificação de expurgo de dados       | QA      | TODO   |                |            |       |
| Testar em staging antes de produção                                   | QA      | TODO   |                |            |       |
| Documentar critérios de aceitação para testes                        | QA      | TODO   |                |            |       |

## Testes de Segurança (Prazo: 2026-02-23, Responsável: QA Security)

| Item                                                 | Owner | Status | Date Completed | Issue Link | Notes |
| ---------------------------------------------------- | ----- | ------ | -------------- | ---------- | ----- |
| Tentar injeção de prompt (jailbreak)                 | QA    | TODO   |                |            |       |
| Testar limites de taxa (Rate Limiting) e spam        | QA    | TODO   |                |            |       |
| Validar tratamento de erros (não expor stack traces) | Dev   | TODO   |                |            |       |

## Sign-off

| Role             | Name | Date       | Signature |
| ---------------- | ---- | ---------- | --------- |
| Tech Lead        |      |            |           |
| Security Officer |      |            |           |
| DevOps Lead      |      |            |           |
| Legal Counsel    |      |            |           |

## ChromaDB Security Checklist

| Item                                                                                     | Owner  | Status | Date Completed | Issue Link | Notes |
| ---------------------------------------------------------------------------------------- | ------ | ------ | -------------- | ---------- | ----- |
| Enable authentication for ChromaDB (user/password or token-based)                        | DevOps | TODO   |                |            |       |
| Verify authentication is enforced by testing unauthorized access                         | DevOps | TODO   |                |            |       |
| Require TLS/SSL for all client-server connections                                        | DevOps | TODO   |                |            |       |
| Verify certificates and reject plaintext connections                                     | DevOps | TODO   |                |            |       |
| Ensure backups are encrypted at rest                                                     | DevOps | TODO   |                |            |       |
| Document encryption method and verification process                                      | DevOps | TODO   |                |            |       |
| Validate secure persistence and file permissions (chmod 600 for sensitive files)          | DevOps | TODO   |                |            |       |
| Verify that ChromaDB data files are not world-readable                                   | DevOps | TODO   |                |            |       |
| Document all security configurations and verification steps                              | DevOps | TODO   |                |            |       |
| Add ChromaDB security checks to CI/CD pipeline                                           | DevOps | TODO   |                |            |       |
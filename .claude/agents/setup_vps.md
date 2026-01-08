# Setup VPS: Sherlock Discord Bot

## Informações do Ambiente

- **Sistema Operacional:** Linux 24.04.5 LTS (Kernel 5.10.234-1, Debian)
- **Setup de Desenvolvimento:** MacBook Air M3 (8GB RAM).
  - _Nota: É necessário realizar o build multi-arch (linux/amd64) devido à arquitetura ARM64 do host
    de desenvolvimento._
- **Infraestrutura:** Portainer e Traefik já configurados e operacionais.
- **Rede Docker:** `ProfRamosNet` (External).

## Objetivo

Implementar o deploy do `sherlock-discord-bot` utilizando Docker Swarm.

## Fluxo de Implementação

1. **Registry:** Realizar o build e push da imagem para o Docker Hub (suportando a arquitetura do
   servidor).
2. **Orquestração:** Deploy na VPS via Docker Swarm (Stack).
3. **Configuração:**
   - As variáveis de ambiente serão declaradas diretamente no arquivo `docker-compose.yml`, dado que
     o uso é estritamente interno.
   - O serviço deve ser anexado à rede externa `ProfRamosNet`.

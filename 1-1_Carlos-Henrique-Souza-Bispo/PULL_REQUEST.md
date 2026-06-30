# Pull Request — RetentionAI

## Título sugerido

```text
1-1_Carlos-Henrique-Souza-Bispo
```

## Descrição para copiar no GitHub

### Projeto Final — Trilha 1.1: Previsão de churn

Este Pull Request entrega o **RetentionAI**, um agente auditável de apoio à retenção de
clientes. O sistema recebe o perfil contratual de um cliente, estima a probabilidade de
churn, explica os sinais que mais influenciaram a previsão e sugere ações priorizadas para
uma abordagem humana.

**Autor:** Carlos Henrique de Souza Bispo  
**Matrícula:** 211061529  
**Relatório:** [README do projeto](./1-1_Carlos-Henrique-Souza-Bispo/README.md)  
**Aplicação:** `[ADICIONAR URL PÚBLICA]`  
**Vídeo:** [demonstração no YouTube](https://youtu.be/SEU_VIDEO_ID)

### O que foi entregue

- pipeline reproduzível de download, preparação, treino e avaliação;
- regressão logística interpretável treinada no IBM Telco Customer Churn;
- agente que orquestra predição, explicação local e playbook de retenção;
- API FastAPI com documentação OpenAPI em `/docs`;
- interface web responsiva integrada à API;
- guardrails estruturais, validações de coerência e mensagens amigáveis;
- fallback heurístico para indisponibilidade ou falha do modelo;
- monitoramento de latência, faixa de risco e taxa de fallback sem persistir o perfil;
- empacotamento com Docker e Docker Compose;
- testes unitários e de integração;
- relatório, Data Card e Model Card.

### Arquitetura resumida

```text
Interface web
    ↓
FastAPI → guardrails de entrada
    ↓
RetentionAgent
    ├── modelo de churn
    ├── explicador local
    ├── playbook de retenção
    └── fallback heurístico
    ↓
guardrails de saída → resposta auditável + telemetria
```

### Resultados

O modelo foi avaliado em um conjunto de teste estratificado com 1.409 registros:

| Métrica | Resultado |
|---|---:|
| ROC-AUC | 0,8419 |
| PR-AUC | 0,6338 |
| Recall | 0,9225 |
| Precision | 0,4378 |
| F1 | 0,5938 |
| F2 | 0,7553 |

O limiar de decisão de 0,1412 foi escolhido pela maior pontuação F2, priorizando recall
para reduzir falsos negativos em um cenário de triagem. A aplicação não executa ações
automaticamente: a decisão final permanece com o atendente.

### Como executar

```bash
cd 1-1_Carlos-Henrique-Souza-Bispo
docker compose up --build
```

Depois, acessar:

- interface: <http://localhost:8000>;
- documentação da API: <http://localhost:8000/docs>;
- saúde do serviço: <http://localhost:8000/health>;
- métricas operacionais: <http://localhost:8000/api/v1/metrics>.

### Evidências de qualidade

```text
pytest:             10 testes aprovados
cobertura:          80,58%
ruff check:         aprovado
smoke test local:   interface HTTP 200, modelo carregado e predição concluída
```

Os testes cobrem contrato de entrada, combinações inválidas de serviços, API, interface,
fallback, privacidade dos logs e seleção do limiar.

### Dados, licença e ética

A cópia utilizada do IBM Telco Customer Churn integra o repositório oficial da IBM sob
Apache License 2.0. O CSV não é versionado neste PR e é baixado diretamente da fonte pelo
pipeline de treino.

O produto é destinado somente a apoio à decisão. Ele não deve negar atendimento, alterar
preços ou limitar direitos. Os recortes de avaliação mostram uma taxa de falsos positivos
maior para clientes idosos; essa diferença está registrada no Model Card e exige
monitoramento antes de qualquer uso real.

### Checklist da entrega

- [x] Pasta no padrão da trilha e projeto
- [x] Relatório completo no README
- [x] Fonte e licença dos dados documentadas
- [x] Modelo treinado e métricas registradas
- [x] Agente com ferramentas e resposta acionável
- [x] API e interface integradas
- [x] Guardrails e fallback
- [x] Docker e instruções de reprodução
- [x] Testes automatizados
- [x] Data Card e Model Card
- [ ] URL pública adicionada ao README e a este PR
- [ ] Vídeo publicado e `SEU_VIDEO_ID` substituído
- [ ] Screenshot ou GIF da aplicação anexado abaixo

### Demonstração visual

> Arraste aqui uma imagem ou um GIF curto mostrando o formulário e o resultado da análise.

### Observações para revisão

O caminho principal para avaliação é:

1. executar `docker compose up --build`;
2. abrir a interface e selecionar o exemplo de alto risco;
3. conferir fatores e recomendações;
4. selecionar o exemplo de baixo risco para comparação;
5. consultar `/docs`, `/health` e `/api/v1/model-card`;
6. consultar o README para decisões, limitações, ética e próximos passos.


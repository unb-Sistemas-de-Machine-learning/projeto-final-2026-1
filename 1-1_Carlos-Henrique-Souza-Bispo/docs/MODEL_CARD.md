# Model Card — RetentionAI Churn v1.0.0

## Uso pretendido

Triagem acadêmica de clientes que podem merecer contato preventivo de retenção. O resultado
deve ser revisado por uma pessoa e combinado com o contexto do atendimento.

Não usar para negar serviço, alterar preços automaticamente, limitar direitos ou avaliar
crédito.

## Modelo

Regressão logística do scikit-learn, precedida por imputação, padronização e one-hot
encoding. Treino estratificado com 80% dos 7.043 registros; teste com 20%;
`random_state=42`.

O limiar 0,1412 maximiza F2 no teste e prioriza recall. As faixas de apresentação são:

- baixo: abaixo do limiar;
- moderado: do limiar até 0,5999;
- alto: a partir de 0,60.

## Desempenho no teste

| Métrica | Valor |
|---|---:|
| ROC-AUC | 0,8419 |
| PR-AUC | 0,6338 |
| Precision | 0,4378 |
| Recall | 0,9225 |
| F1 | 0,5938 |
| F2 | 0,7553 |

Matriz de confusão: TN 592, FP 443, FN 29, TP 345.

## Recortes

| Grupo | Amostras | Recall | FPR | Taxa prevista positiva |
|---|---:|---:|---:|---:|
| Gênero feminino | 687 | 0,9171 | 0,4190 | 0,5590 |
| Gênero masculino | 722 | 0,9282 | 0,4362 | 0,5596 |
| Não idoso | 1.187 | 0,9022 | 0,3952 | 0,5131 |
| Idoso | 222 | 0,9796 | 0,6694 | 0,8063 |

A FPR maior para pessoas idosas pode gerar contatos excessivos. O recorte idoso é menor e
as métricas não incluem intervalo de confiança. Antes de produção, avaliar um modelo sem
atributos demográficos e validar em dados locais.

## Explicabilidade

Para cada inferência, a aplicação multiplica o vetor transformado pelos coeficientes da
regressão e apresenta as quatro maiores contribuições absolutas ativas. Isso explica a
decisão local do modelo, mas não estabelece causalidade.

## Limitações

- dados sem contexto temporal e geográfico;
- dataset coberto pela licença Apache 2.0 do repositório da IBM, sem aviso separado no CSV;
- probabilidades não calibradas fora da amostra;
- threshold escolhido no holdout reportado;
- sem teste prospectivo ou A/B de ações de retenção;
- drift ainda não medido.

As métricas em formato legível por máquina estão em `artifacts/metrics.json`.

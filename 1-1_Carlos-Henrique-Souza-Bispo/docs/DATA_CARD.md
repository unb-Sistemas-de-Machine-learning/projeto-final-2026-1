# Data Card — IBM Telco Customer Churn

## Resumo

Base tabular com 7.043 perfis de clientes de telecomunicações e 21 colunas. O alvo
`Churn` informa se o cliente cancelou. A taxa positiva é 26,54%.

## Origem

- mantenedor da cópia usada: IBM;
- arquivo:
  <https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv>;
- acesso no treino: download HTTPS pelo módulo `app.training`;
- snapshot treinado: 30/06/2026.

## Licença e uso

A cópia usada integra o repositório oficial da IBM
`telco-customer-churn-on-icp4d`, licenciado sob
[Apache License 2.0](https://github.com/IBM/telco-customer-churn-on-icp4d/blob/master/LICENSE).
O arquivo não apresenta um aviso separado ou uma exceção de licença. Este projeto mantém a
atribuição à IBM e não versiona o CSV: o pipeline o baixa diretamente da fonte.

## Campos usados

- numéricos: `tenure`, `MonthlyCharges`, `TotalCharges`;
- demográficos: `gender`, `SeniorCitizen`, `Partner`, `Dependents`;
- serviços: telefone, internet, segurança, backup, proteção, suporte e streaming;
- contrato: duração, fatura digital e forma de pagamento;
- alvo: `Churn`.

`customerID` é removido. Valores vazios de `TotalCharges` são imputados pela mediana dentro
do pipeline, sem consultar o conjunto de teste durante o ajuste.

## Qualidade, representatividade e vieses

A descrição pública não informa período, país, método de amostragem ou se os registros são
reais ou simulados. Categorias como gênero são binárias e não representam a diversidade de
identidades. O comportamento de churn pode ter mudado desde a criação da amostra.

O dataset não deve ser usado para:

- tomar decisões autônomas sobre clientes;
- estimar risco em outra operadora sem validação local;
- inferir causalidade entre um atributo e o cancelamento;
- discriminar atendimento, preço ou acesso a benefícios.

## Dados de inferência

Em produção, os dados novos viriam do cadastro e do sistema de billing da operadora. Neste
MVP, um atendente informa os valores no formulário ou outro sistema chama a API. O
identificador opcional não entra no modelo nem é persistido.

# Segurança desta demonstração

Este repositório foi criado do zero para ser público. Ele **não** é uma cópia do sistema em
produção, e o histórico do Git não contém nada do sistema original.

- **Dados inventados.** POPs com nomes genéricos, seriais `DEMO0001…`, nenhum nome de cliente
  ou órgão real.
- **IPs de documentação.** Todos os endereços estão nas faixas reservadas pela RFC 5737
  (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`), que não existem na internet. Um teste
  automático falha se aparecer qualquer outro endereço.
- **Sem integrações reais.** Não há cliente do Zabbix, SSH, SNMP ou acesso a equipamentos
  nesta edição. `DATA_SOURCE` diferente de `demo` encerra o programa com erro.
- **Sem segredos.** Não há `.env` com valores, tokens, chaves ou certificados. O `.gitignore`
  bloqueia esses arquivos por precaução.
- **Somente leitura.** A única gravação é a das ocorrências, e ela fica na memória do processo.

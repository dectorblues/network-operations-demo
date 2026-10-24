# Arquitetura

## Camadas

1. **Fonte de dados** (`app/sources.py`). Entrega POPs, equipamentos e eventos no formato de
   `app/models.py`. A escolha é feita pela variável `DATA_SOURCE`. No sistema original existe
   uma fonte que lê a API do Zabbix (hosts, itens e triggers, com cache curto). Nesta edição só
   existe a fonte `demo`.
2. **Regras** (`app/rules.py`). Funções puras: recebem os dados e devolvem estado,
   resumo por POP e alarmes agrupados. Não fazem rede nem acessam disco, então são fáceis de
   testar.
3. **API** (`app/main.py`). FastAPI com rotas de leitura (`/api/noc`, `/api/devices`,
   `/api/topology`, `/api/onus`) e as rotas das ocorrências.
4. **Páginas** (`pages/*.html` + `static/`). HTML e JavaScript puros, que leem a API e se
   atualizam a cada 30 segundos.

## Decisões

- **Agrupar alarmes pela causa.** Quando um POP cai, o operador precisa de uma linha dizendo
  "POP fora, verificar o link", e não de vinte linhas de "sem ping".
- **Separar "fora" de "sem coleta".** A falta de dado novo pode ser problema do monitoramento,
  não do equipamento.
- **Ignorar valores de rádio sem associação.** −96 dBm e CCQ 0% indicam rádio sem estação
  associada; tratar como "sinal ruim" gera diagnóstico errado.
- **Regras separadas da fonte.** Trocar o monitoramento não muda a lógica, e os testes rodam
  sem nenhum servidor externo.
- **Leitura x escrita.** No sistema original, leitura e gravação no monitoramento usam tokens
  diferentes, com permissões mínimas. A demo é somente leitura (`writable = False`).

## Testes

`tests/test_rules.py` cobre classificação, rádio, ONU, energia e agrupamento de alarmes, e
confere que a rede de demonstração mostra todos os cenários. `tests/test_api.py` cobre as
rotas, o fluxo completo de uma ocorrência e as validações.

# sismigra-analytics

Pipeline em Python + DuckDB sobre os microdados públicos do SISMIGRA
(Sistema de Registro Nacional Migratório), com arquitetura em camadas
(bronze, prata, ouro), governança e qualidade de dados, e saídas para BI.

> **Status:** em construção. Etapa atual: **Etapa 0, inventário das colunas reais.**
> O modelo de dados só será definido depois dessa inspeção.

## Etapa 0: inventário dos arquivos

O arquivo do SISMIGRA é publicado em uma pasta do SharePoint do Ministério da
Justiça, dentro de um ZIP. Baixe o arquivo manualmente e rode:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (no Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
python scripts/etapa0_inventario.py "CAMINHO\PARA\A\PASTA"
```

O script aceita um CSV, um ZIP ou uma pasta. Ele gera
`reports/inventario/inventario.md` e `reports/inventario/inventario.json`
com a estrutura de cada coluna (tipo inferido, ausentes, cardinalidade e
categorias mais frequentes). Nenhuma linha dos microdados é copiada.

## Licença

MIT. Veja [LICENSE](LICENSE).

.PHONY: run test dbt-build dbt-docs refs inventario limpar

run:          ## comando único: bronze (Python), dbt build, exportação, divulgação e qualidade
	python -m sismigra.pipeline

test:         ## testes do pytest (incluem o dbt build com dados sintéticos)
	pytest

dbt-build:    ## só o dbt build sobre o banco já carregado (data/sismigra.duckdb)
	python -c "from sismigra.config import Config; from sismigra import dbt_runner; dbt_runner.executar(Config(), 'build')"

dbt-docs:     ## site do dbt docs com dados sintéticos (dbt/target/static_index.html)
	python -m sismigra.sinteticos data/sinteticos --docs

refs:         ## regenera as tabelas de referência (requer requirements-dev.txt)
	python scripts/construir_refs.py --dtb $(DTB) --sismigra data/landing

inventario:   ## inventário estrutural dos arquivos em data/landing
	python scripts/etapa0_inventario.py data/landing

limpar:       ## apaga as saídas geradas (mantém data/landing)
	rm -rf data/bronze data/gold data/sismigra.duckdb data/sinteticos dbt/target dbt/logs dbt/seeds

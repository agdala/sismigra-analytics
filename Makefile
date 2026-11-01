.PHONY: run test refs inventario limpar

run:          ## roda o pipeline completo (bronze, prata, ouro, qualidade)
	python -m sismigra.pipeline

test:         ## roda os testes
	pytest

refs:         ## regenera as tabelas de referência (requer requirements-dev.txt)
	python scripts/construir_refs.py --dtb $(DTB) --sismigra data/landing

inventario:   ## inventário estrutural dos arquivos em data/landing
	python scripts/etapa0_inventario.py data/landing

limpar:       ## apaga as saídas geradas (mantém data/landing)
	rm -rf data/bronze data/silver data/gold

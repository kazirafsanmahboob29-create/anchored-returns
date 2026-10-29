.PHONY: test serve national factors prediction verify-evidence

test:
	python -m scripts.check_calculations

serve:
	python -m src.research serve --snapshot

national:
	python -m src.research national

factors:
	python -m src.research factors
	Rscript analysis/factors.R reports/factor-study
	python -c 'from src.factor_study import package; package()'

verify-evidence:
	python -m src.research check --full

prediction:
	python -m src.prediction_audit
	Rscript analysis/prediction_audit.R reports/prediction-audit
	python -m src.prediction_audit --verify-r

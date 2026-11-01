.PHONY: test serve national factors prediction expanded filing peers reproduce comparability paper verify-evidence

test:
	python -m scripts.check_public_release

serve:
	python -m http.server 8765 --bind 127.0.0.1

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

expanded:
	python -m src.expanded_study
	Rscript analysis/expanded.R reports/expanded-study
	python -m src.expanded_study --verify-r

filing:
	python -m src.filing_study
	Rscript analysis/filing.R reports/filing-study
	python -m src.filing_study --verify-r

peers:
	python -m src.peer_study
	Rscript analysis/peer.R reports/peer-study

reproduce:
	python -m scripts.reproduce_filing --with-r

comparability:
	python -m scripts.analyze_comparability
	Rscript analysis/comparability_check.R

paper:
	python paper/build.py

include .env
STC_API_HOST?=taiga.archi.fr
STC_API_FORWARD_PORT?=1337

.DEFAULT_GOAL := help
help:
	@printf "\033[33mUsage:\033[0m\n  make [target] [arg=\"val\"...]\n\n\033[33mTargets:\033[0m\n"
	@grep -E '^[-a-zA-Z0-9_\.\/]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) \
		| sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[32m%-15s\033[0m %s\n", $$1, $$2}'


run-crawler: ## Lance le crawler Sesame - Taiga avec python !
	@python main.py

install-deps: ## Installe les dépendances python
	@printf "\033[33mPIP:\033[0m install required dependencies ...\n"
	@pip install -r requirements.txt
	@printf "\033[33mPIP:\033[0m SUCCESSFUL !!!\n"

taiga-forward: ## Transfert les appels de l'API Taiga via un proxy socks au travers du serveur sesame (à utiliser pour lancer le script à distance)
	@printf "\033[33mNCAT:\033[0m Launch forwarding tcp requests ...\n"
	@ssh libertech@193.52.197.92 "pkill -f 'ncat taiga.archi.fr 443'" || true
	@ssh libertech@193.52.197.92 "ncat --keep-open --no-shutdown -v \
		--sh-exec 'ncat taiga.archi.fr 443' \
		-l 1337"
	@printf "\033[33mNCAT:\033[0m End of forwarding requests !\n"

update-reqs: ## Met à jour la liste des dépendances python
	@printf "\033[33mUPDATE:\033[0m pipreqs dependency ...\n"
	@pip install pipreqs > ./logs/update-reqs.log
	@printf "\033[33mUPDATE:\033[0m requirements.txt ...\n"
	python -m pipreqs.pipreqs --force .
	@printf "\033[33mUPDATE:\033[0m SUCCESSFUL !!!\n"

STC_API_TARGET?=193.52.197.92
STC_API_HOST?=taiga.archi.fr
STC_API_FORWARD_PORT?=1337
IMG_NAME = "ghcr.io/libertech-fr/sesame-taiga_crawler"
BASE_NAME = "sesame"
APP_NAME = "sesame-taiga_crawler"
PLATFORM = "linux/amd64"
STC_RUN = "all"
STC_IMPORTS = "all"
STC_FORCE = "0"
include .env

.DEFAULT_GOAL := help
help:
	@printf "\033[33mUsage:\033[0m\n  make [target] [arg=\"val\"...]\n\n\033[33mTargets:\033[0m\n"
	@grep -E '^[-a-zA-Z0-9_\.\/]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) \
		| sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[32m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Construit l'image docker
	@printf "\033[33mDOCKER:\033[0m Build docker image ...\n"
	@docker build -t $(IMG_NAME) .
	@printf "\033[33mDOCKER:\033[0m SUCCESSFUL !!!\n"

pull-crawler-docker: ## Pull l'image docker
	@docker pull $(IMG_NAME)

run-crawler-docker: ## Lance le crawler Sesame - Taiga avec python !
	@docker run --rm -it \
		--add-host host.docker.internal:host-gateway \
		--network dev \
		--platform $(PLATFORM) \
		--name $(APP_NAME) \
		-v $(CURDIR):/data \
		$(IMG_NAME) python main.py --run=$(STC_RUN) --imports=$(STC_IMPORTS) --force $(STC_FORCE)

run-crawler: ## Lance le crawler Sesame - Taiga avec python !
	@python3 main.py

install-deps: ## Installe les dépendances python
	@printf "\033[33mPIP:\033[0m install required dependencies ...\n"
	@pip install -r requirements.txt
	@printf "\033[33mPIP:\033[0m SUCCESSFUL !!!\n"

taiga-forward: ## Transfert les appels de l'API Taiga via un proxy socks au travers du serveur sesame (à utiliser pour lancer le script à distance)
	@printf "\033[33mNCAT:\033[0m Launch forwarding tcp requests for <$(STC_API_HOST)> ...\n"
	@ssh libertech@$(STC_API_TARGET) "pkill -f 'ncat $(STC_API_HOST) 443'" || true
	@ssh libertech@$(STC_API_TARGET) "ncat --keep-open --no-shutdown -v \
		--sh-exec 'ncat $(STC_API_HOST) 443' \
		-l $(STC_API_FORWARD_PORT)"
	@printf "\033[33mNCAT:\033[0m End of forwarding requests !\n"

update-reqs: ## Met à jour la liste des dépendances python
	@printf "\033[33mUPDATE:\033[0m pipreqs dependency ...\n"
	@pip install pipreqs > ./logs/update-reqs.log
	@printf "\033[33mUPDATE:\033[0m requirements.txt ...\n"
	python -m pipreqs.pipreqs --force .
	@printf "\033[33mUPDATE:\033[0m SUCCESSFUL !!!\n"

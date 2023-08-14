SHELL:=/bin/bash
PROJECT=diyhue
VERSION=2.0.0
VENV=${PROJECT}-${VERSION}
VENV_DIR=$(shell pyenv root)/versions/${VENV}
PYTHON=${VENV_DIR}/bin/python
DIYHUE_ENV_NAME=${VENV}
DIYHUE_PORT=8888

## Make sure you have `pyenv` and `pyenv-virtualenv` installed beforehand
##
## https://github.com/pyenv/pyenv
## https://github.com/pyenv/pyenv-virtualenv
##
## On a Mac: $ brew install pyenv pyenv-virtualenv
##
## Configure your shell with $ eval "$(pyenv virtualenv-init -)"
##

# .ONESHELL:
DEFAULT_GOAL: help
.PHONY: help run clean build venv ipykernel update diyhue

# Colors for echos
ccend=$(shell tput sgr0)
ccbold=$(shell tput bold)
ccgreen=$(shell tput setaf 2)
ccso=$(shell tput smso)

clean: ## >> remove all environment and build files
	@echo ""
	@echo "$(ccso)--> Removing virtual environment $(ccend)"
	pyenv virtualenv-delete --force ${VENV}
	rm .python-version

requisites: $(UNAME)

Darwin:
	brew update
	brew install pyenv pyenv-virtualenv

Linux:
	git clone https://github.com/pyenv/pyenv.git ~/.pyenv
	echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bash_profile
	echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bash_profile
	exec "$SHELL"
	. ~/.bash_profile
	echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.bash_profile


build: ##@main >> build the virtual environment with an ipykernel for diyhue and install requirements
	@echo ""
	@echo "$(ccso)--> Build $(ccend)"
	$(MAKE) install
	$(MAKE) ipykernel

venv: $(VENV_DIR) ## >> setup the virtual environment

$(VENV_DIR):
	@echo "$(ccso)--> Install and setup pyenv and virtualenv $(ccend)"
	python3 -m pip install --upgrade pip
	pyenv virtualenv ${PYTHON_VERSION} ${VENV}
	echo ${VENV} > .python-version

install: venv requirements.txt ##@main >> update requirements.txt inside the virtual environment
	@echo "$(ccso)--> Updating packages $(ccend)"
	$(PYTHON) -m pip install -r requirements.txt

ipykernel: venv ##@main >> install a Jupyter iPython kernel using our virtual environment
	@echo ""
	@echo "$(ccso)--> Install ipykernel to be used by diyhue notebooks $(ccend)"
	$(PYTHON) -m pip install ipykernel diyhue diyhue_contrib_nbextensions
	$(PYTHON) -m ipykernel install
					--user
					--name=$(VENV)
					--display-name=$(DIYHUE_ENV_NAME)
	$(PYTHON) -m diyhue nbextension enable --py widgetsnbextension --sys-prefix

diyhue: venv ##@main >> start a diyhue notebook
	@echo ""
	@"$(ccso)--> Running diyhue on port $(DIYHUE_PORT) $(ccend)"
	diyhue notebook --port $(DIYHUE_PORT)


# And add help text after each target name starting with '\#\#'
# A category can be added with @category
HELP_FUN = \
	%help; \
	while(<>) { push @{$$help{$$2 // 'options'}}, [$$1, $$3] if /^([a-zA-Z\-\$\(]+)\s*:.*\#\#(?:@([a-zA-Z\-\)]+))?\s(.*)$$/ }; \
	print "usage: make [target]\n\n"; \
	for (sort keys %help) { \
	print "${WHITE}$$_:${RESET}\n"; \
	for (@{$$help{$$_}}) { \
	$$sep = " " x (32 - length $$_->[0]); \
	print "  ${YELLOW}$$_->[0]${RESET}$$sep${GREEN}$$_->[1]${RESET}\n"; \
	}; \
	print "\n"; }

help: ##@other >> Show this help.
	@perl -e '$(HELP_FUN)' $(MAKEFILE_LIST)
	@echo ""
	@echo "Note: to activate the environment in your local shell type:"
	@echo "   $$ pyenv activate $(VENV)"

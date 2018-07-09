all: build run

build:
	pip install -r requirements.txt

run-%: check-env
	SIMPLE_SETTINGS=settings.$* FLASK_APP=usma.py flask run

check-env:
ifndef JIRA_ADDR
    $(error JIRA_ADDR is undefined)
endif


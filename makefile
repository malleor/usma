all: build run

build:
	pip install -r requirements.txt

run-%:
	SIMPLE_SETTINGS=settings.$* FLASK_APP=usma.py flask run

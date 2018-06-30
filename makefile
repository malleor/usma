all: build run

build:
	pip install -r requirements.txt

run:
	FLASK_APP=usma.py flask run

PY=python3.12

run:
	. venv/bin/activate; $(PY) -m fastapi dev app-fastapi.py

install:
	# Sudo is needed for creating /www folder
	sudo mkdir /www
	sudo chown 1000 /www
	sudo chmod 755 /www
	
	$(PY) -m venv venv
	. venv/bin/activate; $(PY) -m pip install --upgrade pip
	. venv/bin/activate; $(PY) -m pip install -r requirements.txt

PY=python3.12

run:
	venv-$(PY)/bin/python -m uvicorn app-fastapi:app \
		--host 0.0.0.0 --port 443 \
		--ssl-keyfile privkey.pem \
		--ssl-certfile fullchain.pem

dev: test.pem
	venv-$(PY)/bin/python -m uvicorn app-fastapi:app \
		--host 0.0.0.0 --port 8443 --reload \
		--ssl-keyfile test.pem \
		--ssl-certfile test.pem

install:
	sudo mkdir -p /www
	sudo chown 1000 /www
	sudo chmod 755 /www
	mkdir -p /www/restricted
	mkdir -p /www/.well-known/acme-challenge
	
	$(PY) -m venv venv-$(PY)
	venv-$(PY)/bin/python -m pip install --upgrade pip
	venv-$(PY)/bin/python -m pip install -r requirements.txt
	
	sudo setcap CAP_NET_BIND_SERVICE=+eip \
		$$(readlink -f venv-$(PY)/bin/python)
	
	sudo cp -f tir-na-nog.service /etc/systemd/system
	sudo systemctl daemon-reload
	
	@printf '\n\033[38;2;255;224;0m!!!! '
	@printf 'Run make certify as well (don$'t know how long until expiry)'
	@printf ' !!!!\033[0m\n\n'

certify:
	sudo certbot certonly --email 'nathan.yinger@gmail.com' --agree-tos \
	--non-interactive -d 'tir-na-nog.den-antares.com' --webroot -w /www
	
	@printf '\n\033[38;2;255;224;0m'
	# !!!! Verify certificate and key are in the same place !!!!
	@printf '\033[0m\n'
	
	sudo cp /etc/letsencrypt/live/tir-na-nog.den-antares.com/privkey.pem privkey.pem
	sudo cp /etc/letsencrypt/live/tir-na-nog.den-antares.com/fullchain.pem fullchain.pem
	sudo chown 1000 *.pem
	sudo chgrp 1000 *.pem
	sudo chmod 755 *.pem

test.pem:
	openssl req -x509 -out test.pem -keyout test.pem -newkey rsa:3072 \
		-nodes -sha256 -subj '/CN=test' -days 10000

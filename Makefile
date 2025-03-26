PY=python3.12

# Do not attempt to run servers on ports below 1024. Even if permissions are
# granted by setcap, they can randomly disappear later. Setcap permissions
# should not be relied on in production
run:
	venv-$(PY)/bin/python -m uvicorn app-fastapi:app \
		--host 0.0.0.0 --port 9000 --use-colors

dev:
	@printf '\n\033[38;2;255;224;0m!!!! '
	@printf 'Run `caddy run` from this folder in another terminal'
	@printf ' !!!!\033[0m\n\n'
	
	venv-$(PY)/bin/python -m uvicorn app-fastapi:app \
		--host 0.0.0.0 --port 9000 --use-colors --reload

install: test-cert.pem
	# Written for Fedora
	sudo dnf install -y caddy
	sudo setsebool -P nis_enabled 1
	
	sudo mkdir -p /www
	sudo chmod 755 /www
	sudo chown -R 1000:1000 /www
	sudo chcon -R -t httpd_sys_content_t /www
	# Note: httpd_sys_rw_content_t is also available for content that Caddy
	# needs to be able to write
	mkdir -p /www/files/restricted
	
	mkdir -p /www/logs
	sudo chown -R caddy:caddy /www/logs
	sudo chcon -R -t httpd_log_t /www/logs
	sudo -u caddy touch /www/logs/access-test.log /www/logs/access-prod.log
	
	$(PY) -m venv venv-$(PY)
	venv-$(PY)/bin/python -m pip install --upgrade pip
	venv-$(PY)/bin/python -m pip install -r requirements.txt
	
	sudo cp -f *.service /etc/systemd/system
	sudo systemctl daemon-reload
	
ifneq "$(shell pwd -P)" "/www/tir-na-nog"
	cd .. && sudo mv tir-na-nog /www/tir-na-nog
	ln -s /www/tir-na-nog ..
	sudo chcon -R -t httpd_sys_content_t /www/tir-na-nog
	
	@printf '\n\033[38;2;0;255;255m!!!! '
	@printf 'Repo was moved to /www/tir-na-nog and a symlink left in its '
	@printf 'place. Run `cd ../tir-na-nog` to follow new link'
	@printf ' !!!!\033[0m\n\n'
endif

test-cert.pem:
	openssl req -x509 -out test-cert.pem -keyout test-key.pem \
		-newkey rsa:3072 -nodes -sha256 -subj "/CN=$$HOSTNAME" \
		-days 10000
	
	chown caddy:caddy test-cert.pem test-key.pem

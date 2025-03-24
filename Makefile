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

install:
	# Written for Fedora
	sudo dnf install -y caddy
	
	sudo mkdir -p /www
	sudo chmod 755 /www
	sudo chown 1000:1000 /www
	mkdir -p /www/restricted
	
	$(PY) -m venv venv-$(PY)
	venv-$(PY)/bin/python -m pip install --upgrade pip
	venv-$(PY)/bin/python -m pip install -r requirements.txt
	
	sudo cp -f tir-na-nog.service /etc/systemd/system
	sudo systemctl daemon-reload
	
ifneq "$(shell pwd -P)" "/www-tir-na-nog"
	cd .. && sudo mv tir-na-nog /www-tir-na-nog
	ln -s /www-tir-na-nog ../tir-na-nog
	
	@printf '\n\033[38;2;0;255;255m!!!! '
	@printf 'Repo was moved to /www-tir-na-nog and a symlink left in its '
	@printf 'place. Run `cd ../tir-na-nog` to follow new link'
	@printf ' !!!!\033[0m\n\n'
endif

install-prod:
	# Caddy's unit file is in a different place. Idk why.
	sudo cp -f caddy.service /usr/lib/systemd/system
	sudo systemctl daemon-reload
	
	sudo systemctl enable --now caddy
	sudo systemctl enable --now tir-na-nog

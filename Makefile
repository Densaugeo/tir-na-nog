# Written for Fedora
PY=python3.12
USER_PREFIX=tir-na-nog

RESET=\x1b[0m
BOLD=\x1b[1m
ORANGE=\x1b[38;2;246;116;0m
WHITE=\x1b[38;2;255;255;255m


install:
	sudo dnf install apptainer tmux
	python apptainers/cluster-runner.py install $(USER_PREFIX)

dev: www-dev
	python apptainers/cluster-runner.py run www-dev $(USER_PREFIX) \
		tir-na-nog 8080 8443

www-dev:
	python apptainers/cluster-runner.py deploy $@ $(USER_PREFIX) \
		root --dev

test: www-test
	python apptainers/cluster-runner.py run www-test $(USER_PREFIX) \
		test 7080 7443

www-test:
	python apptainers/cluster-runner.py deploy $@ $(USER_PREFIX) \
		root

clean:
	rm -rf www-dev www-test

commission: /www
	sudo python apptainers/cluster-runner.py daemonize /www \
		$(USER_PREFIX) 6080 6443

/www:
	python apptainers/cluster-runner.py deploy $@ $(USER_PREFIX) \
		root

monitor:
	python apptainers/cluster-runner.py monitor /www $(USER_PREFIX) \
		tir-na-nog-prod

decommission:
	@printf '\n$(BOLD)$(ORANGE)Warning: $(WHITE)All files under '
	@printf '$(ORANGE)/www $(WHITE)will be deleted!$(RESET)\n\n'
	
	@printf 'Press enter to continue, or exit with Ctrl+C\n'
	@read
	
	sudo python apptainers/cluster-runner.py clear-daemons $(USER_PREFIX)
	sudo rm -rf /www

uninstall:
	python apptainers/cluster-runner.py uninstall $(USER_PREFIX)



# Is this SELinux stuff needed? Apptainer seems to avoid most SELinux issues,
# but I won't know for sure until I try installing on a fresh OS
selinux-configured.txt:
	sudo setsebool -P nis_enabled 1
	sudo setsebool -P httpd_use_fusefs 1
	@# Allows Caddy to access files labeled user_home_t. This is essential
	@# because this label is often applied to new files
	sudo setsebool -P httpd_read_user_content 1
	
	sudo semanage fcontext -a -t httpd_sys_content_t    "/www(/.*)?"
	sudo semanage fcontext -a -t httpd_config_t         "/www/caddy(/.*)?"
	@# SELinux offers a log type `httpd_log_t`, but it is useless because it
	@# does not allow writing to the logs
	sudo semanage fcontext -a -t httpd_sys_rw_content_t "/www/logs(/.*)?"
	sudo semanage fcontext -a -t httpd_sys_content_t    "/www/sockets(/.*)?"
	sudo semanage fcontext -a -t systemd_unit_file_t    "/www/systemd(/.*)?"
	sudo semanage fcontext -a -t cert_t                 "/www/.*.pem"
	
	touch selinux-configured.txt

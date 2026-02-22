import argparse, pathlib, subprocess, shutil, os, pwd, grp

####################
# Helper Functions #
####################

import re, sys

RESET     = '\x1b[0m'
BOLD      = '\x1b[1m'
FAINT     = '\x1b[2m'
ITALIC    = '\x1b[3m'
UNDERLINE = '\x1b[4m'
BLINK     = '\x1b[5m'
INVERT    = '\x1b[7m'
STRIKE    = '\x1b[9m'
WHITE     = '\x1b[38;2;255;255;255m' #fff
GRAY      = '\x1b[38;2;204;204;204m' #ccc
MAGENTA   = '\x1b[38;2;255;0;255m'   #f0f
VIOLET    = '\x1b[38;2;204;102;255m' #c6f
BLUE      = '\x1b[38;2;68;170;221m'  #4ad
CYAN      = '\x1b[38;2;68;221;221m'  #4dd
AQUA      = '\x1b[38;2;26;186;151m'  #1aba97
GREEN     = '\x1b[38;2;68;221;68m'   #4d4
ORANGE    = '\x1b[38;2;236;182;74m'  #ecb64a
RED       = '\x1b[38;2;255;0;0m'     #f00
WARNING_ORANGE = '\x1b[38;2;246;116;0m' # from KWrite's makefile highlighting

ANSI_COLOR_RE = re.compile('\x1b\\[[0-9;]+m')

def fail(message: str):
    print(f'{BOLD}{RED}Error:{RESET} {message}')
    sys.exit(1)

def shellper(description: str, command: str):
    print(description)
    print(command)
    subprocess.run(ANSI_COLOR_RE.sub('', command), shell=True, check=True)
    print()

def find_app_folders(deployment: pathlib.Path) -> [pathlib.Path]:
    reserved_names = ['logs', 'sockets', 'webroot']
    
    app_folders = [f for f in deployment.iterdir()
        if f.is_dir() and f.name[0] != '.' and f.name not in reserved_names]
    
    app_folders.sort()
    
    for i, folder in enumerate(app_folders):
        if folder.name == 'caddy':
            app_folders.insert(0, app_folders.pop(i))
    
    return app_folders

def mkdir(path: pathlib.Path, mode: int = 0, owner: str = '', group: str = ''):
    if path.exists():
        assert path.is_dir()
    else:
        if os.access(path.parent, os.W_OK):
            os.mkdir(path)
        else:
            subprocess.run(f'sudo mkdir {path}', shell=True, check=True)
    
    # Do not use the mode argument to os.mkdir(), because that applies the umask
    if mode:
        if os.access(path, os.W_OK):
            os.chmod(path, mode)
        else:
            subprocess.run(f'sudo chmod {mode:o} {path}',
                shell=True, check=True)
    
    if owner:
        subprocess.run(f'sudo chown {owner} {path}', shell=True, check=True)
    
    if group:
        subprocess.run(f'sudo chgrp {group} {path}', shell=True, check=True)

def copytree(source: pathlib.Path, destination: pathlib.Path, dir_mode: int = 0,
file_mode: int = 0, link_instead: bool = False):
    if link_instead:
        os.symlink(source.resolve(), destination)
        return
    
    if not source.is_dir():
        shutil.copy2(source, destination)
        if file_mode: os.chmod(destination, file_mode)
        return
    
    shutil.copytree(source, destination, symlinks=True)
    if dir_mode: os.chmod(destination, dir_mode)
    
    for root, dirs, files in os.walk(destination):
        if dir_mode:
            for dir in dirs:
                os.chmod(os.path.join(root, dir), dir_mode)
        
        if file_mode:
            for file in files:
                os.chmod(os.path.join(root, file), file_mode)

def verify_file(path: pathlib.Path, description: str, note: str = ''):
    if not path.exists():
        fail(f'{description} {BOLD}{RED}{path}{RESET} not found! {note}')

def verify_account(name: str, is_group: bool):
    description = 'Group' if is_group else 'User'
    
    try:
        xid = (grp.getgrnam(name).gr_gid if is_group else
            pwd.getpwnam(name).pw_uid)
    except KeyError:
        fail(f'{description} {BOLD}{RED}{name}{RESET} not found!')
    
    # Fedora requires system UIDs/GIDs be within 201-999 (inclusive)
    if not 200 < xid < 1000:
        fail(f'{description} {BOLD}{ORANGE}{name}{RESET} has ID '
            f'{BOLD}{RED}{xid}{RESET} , which is outside the range of '
            f'system UIDs/GIDs for Fedora.')

def verify_user(name: str):
    # As far as I know, every user should have a corresponding group
    verify_account(name, is_group=False)
    verify_account(name, is_group=True)

def verify_group(name: str):
    # However, groups may not have corresponding users (such as www group)
    verify_account(name, is_group=True)

###############
# Subcommands #
###############

def install(user_prefix: str):
    print()
    
    app_folders = find_app_folders(pathlib.Path('apptainers'))
    
    for folder in app_folders:
        verify_file(folder / 'Definitionfile', 'Apptainer definition')
    
    print(f'{ITALIC}{CYAN}Preparing Linux users...{RESET}')
    for folder in app_folders:
        app_name = folder.name
        app_user = f'{user_prefix}-{app_name}'
        
        try:
            pwd.getpwnam(app_user).pw_uid
            print(f'User {BOLD}{VIOLET}{app_user}{RESET} already present')
        except KeyError:
            print(f'Adding user {BOLD}{VIOLET}{app_user}{RESET}')
            subprocess.run(f'sudo useradd --system --create-home {app_user}',
                shell=True, check=True)
        
        print(f'Verifying settings for {BOLD}{VIOLET}{app_user}{RESET}')
        verify_user(app_user)
        
        subprocess.run(f'sudo EDITOR="cp /dev/stdin" '
            f'visudo -f {pathlib.Path('/etc/sudoers.d') / app_user}',
            input=f'%www ALL = ({app_user}) NOPASSWD:ALL\n', text=True,
            shell=True, check=True)
    
    print(f'Adding current user to {BOLD}{VIOLET}www{RESET} group')
    subprocess.run(f'sudo usermod --append --groups www $USER',
        shell=True, check=True)
    
    print()
    
    for folder in app_folders:
        print(f'{ITALIC}{CYAN}Building apptainer image '
            f'{BOLD}{ORANGE}{folder / 'image.sif'} {ITALIC}{CYAN}...{RESET}')
        
        subprocess.run(f'apptainer build -F image.sif Definitionfile',
            cwd=folder, shell=True, check=True)
        
        print()

def uninstall(user_prefix: str):
    print()
    
    app_folders = find_app_folders(pathlib.Path('apptainers'))
    
    print(f'{ITALIC}{CYAN}Removing Linux users...{RESET}')
    for folder in app_folders:
        app_name = folder.name
        app_user = f'{user_prefix}-{app_name}'
        
        try:
            pwd.getpwnam(app_user).pw_uid
        except KeyError:
            print(f'No user {BOLD}{VIOLET}{app_user}{RESET}')
            continue
        
        print(f'Removing user {BOLD}{VIOLET}{app_user}{RESET}')
        subprocess.run(f'sudo userdel {app_user}', shell=True, check=True)
        
        subprocess.run(f'sudo rm -rf /home/{app_user}',
            shell=True, check=True)
        
        subprocess.run(f'sudo rm -f /etc/sudoers.d/{app_user}',
            shell=True, check=True)
    print()
    
    print(f'{ITALIC}{CYAN}Removing built apptainer images...{RESET}')
    for folder in app_folders:
        if (folder / 'image.sif').exists():
            print(f'Deleting {BOLD}{ORANGE}{folder / 'image.sif'}{RESET}')
            os.remove(folder / 'image.sif')
        else:
            print(f'No {BLUE}image.sif{RESET} in {BOLD}{ORANGE}{folder}{RESET}')
    print()

def deploy(target: pathlib.Path, user_prefix: str, webroot: pathlib.Path,
dev: bool):
    print()
    
    if target.exists():
        fail(f'Deployment target {BOLD}{RED}{target}{RESET} already exists!'
            f' Updating existing deployments is not supported yet, please '
            f'create a new one.')
    
    app_folders = find_app_folders(pathlib.Path('apptainers'))
    
    verify_group('www')
    
    for folder in app_folders:
        verify_file(folder / 'image.sif', f'{folder.name} image',
            'App cluster may not have been installed')
        verify_file(folder / 'ro', f'Read-only mount for {folder.name}')
        
        verify_user(f'{user_prefix}-{folder.name}')
    
    print(f'{ITALIC}{CYAN}Creating deployment at {BOLD}{ORANGE}{target} '
        f'{ITALIC}{CYAN}...{RESET}')
    
    print('Building folder structure')
    mkdir(target, mode=0o2775, group='www')
    mkdir(target / 'sockets', mode=0o2775)
    copytree(webroot, target / 'webroot',
        dir_mode=0o2775, file_mode=0o664, link_instead=dev)
    
    for folder in app_folders:
        name = folder.name
        print(f'{'Linking' if dev else 'Copying'} {BLUE}{name}{RESET}')
        mkdir(target / 'sockets' / name, mode=0o2770,
            owner=f'{user_prefix}-{name}', group=f'{user_prefix}-caddy')
        mkdir(target / name, mode=0o2775)
        copytree(folder / 'image.sif', target / name / 'image.sif',
            dir_mode=0o2775, file_mode=0o664, link_instead=dev)
        copytree(folder / 'ro', target / name / 'ro',
            dir_mode=0o2775, file_mode=0o664, link_instead=dev)
        mkdir(target / name / 'rw', mode=0o2775,
            owner=f'{user_prefix}-{name}', group='www')
    print()

def daemonize(deployment: pathlib.Path, user_prefix: str, http_port: int,
https_port: int, fqdn: str):
    print()
    
    if not os.access('/etc/systemd/system', os.W_OK):
        fail('Must be run with sudo')
    
    app_folders = find_app_folders(deployment)
    
    for folder in app_folders:
        service_name = f'{user_prefix}-{folder.name}'
        unit_file_path = pathlib.Path(f'/etc/systemd/system/'
            f'{service_name}.service')
        
        if unit_file_path.exists():
            fail(f'Unit file {BOLD}{RED}{unit_file_path}{RESET} already '
                f'exists! Only one deployment may be daemonized for each user prefix')
    
    print(f'{ITALIC}{CYAN}Daemonizing {BOLD}{ORANGE}{deployment} '
        f'{ITALIC}{CYAN}...{RESET}')
    
    target_file_path = pathlib.Path(f'/etc/systemd/system/'
        f'{user_prefix}.target')
    print(f'Writing {BOLD}{ORANGE}{target_file_path}{RESET}')
    with open(target_file_path, 'w') as f:
        f.write(f'''\
# Autogenerated, do not modify

[Unit]
Description={user_prefix} cluster
Wants={' '.join(f'{user_prefix}-{f.name}.service' for f in app_folders)}
After={' '.join(f'{user_prefix}-{f.name}.service' for f in app_folders)}

[Install]
WantedBy=multi-user.target
''')
    
    for folder in app_folders:
        app_name = folder.name
        app_user = f'{user_prefix}-{app_name}'
        service_name = app_user
        unit_file_path = pathlib.Path(f'/etc/systemd/system/'
            f'{service_name}.service')
        
        print(f'Writing {BOLD}{ORANGE}{unit_file_path}{RESET}')
        
        # LimitNOFILE = 4096 commonly recommended in guides. High value for
        # Caddy from Fedora's Caddy unit file. This should probably be handled
        # via sidecar file at some point
        limit_no_file = 1048576 if app_name == 'caddy' else 4096
        
        if app_name == 'caddy':
            exec_start_pre = (f'python {__file__} caddygen . {http_port} '
                f'{https_port}')
            if fqdn:
                exec_start_pre + f' --fqdn {fqdn}'
            exec_start = ('apptainer run --containall '
                '--bind caddy/ro:/ro:ro --bind caddy/rw:/rw:rw '
                '--bind sockets:/sockets --bind webroot:/webroot:ro '
                'caddy/image.sif')
        else:
            exec_start_pre = ''
            exec_start = (f'apptainer run --containall '
                f'--bind {app_name}/ro:/ro:ro --bind {app_name}/rw:/rw:rw '
                f'--bind sockets/{app_name}:/sockets {app_name}/image.sif')
        
        with open(unit_file_path, 'w') as f:
            f.write(f'''\
# Autogenerated, do not modify

[Unit]
Description={user_prefix} cluster {app_name} app
# Network dependencies copied from Fedora Caddy unit file
After=network.target network-online.target
Requires=network-online.target
PartOf={user_prefix}.target

[Service]
Type=exec
User={app_user}
Group={app_user}
WorkingDirectory={deployment}
Environment="HOSTNAME=%H"
ExecStartPre={exec_start_pre}
ExecStart={exec_start}
Restart=on-failure
RestartSec=1m
RestartSteps=10
RestartMaxDelaySec=24h
TimeoutStopSec=5s
LimitNOFILE={limit_no_file}
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
# WTF SystemD
SuccessExitStatus=143

[Install]
WantedBy={user_prefix}.target
''')
    
    print(f'Reloading SystemD units')
    subprocess.run('systemctl daemon-reload', shell=True, check=True)
    
    print(f'\nSystemD services installed and grouped under '
        f'{BOLD}{AQUA}{user_prefix}.target{RESET} .'
        f' Run {AQUA}systemctl start {BOLD}{user_prefix}.target{RESET} to '
        f'start.\n')

def clear_daemons(user_prefix: str):
    print()
    
    if not os.access('/etc/systemd/system', os.W_OK):
        fail('Must be run with sudo')
    
    print(f'{ITALIC}{CYAN}Searching for daemons...{RESET}')
    
    # You might be able stop/disable all relevant services using the .target
    # unit, but it's easy to screw up the .target file so stop each one
    # individually just to be sure
    for file in pathlib.Path('/etc/systemd/system').iterdir():
        if file.name[:len(user_prefix)] == user_prefix:
            subprocess.run(f'systemctl stop {file.name}',
                shell=True, check=True)
            
            print(f'Disabling {BOLD}{AQUA}{file.name}{RESET}')
            subprocess.run(f'systemctl disable {file.name}',
                shell=True, check=True)
            
            print(f'Deleting {BOLD}{ORANGE}{file}{RESET}')
            os.remove(file)
    
    print(f'Reloading SystemD units')
    subprocess.run('systemctl daemon-reload', shell=True, check=True)
    
    print()

def caddygen(deployment: pathlib.Path, http_port: int, https_port: int,
fqdn: str):
    print(f'{ITALIC}{CYAN}Generating Caddyfile...{RESET}')
    
    snippet = deployment / 'caddy' / 'ro' / 'Caddyfile-snippet'
    verify_file(snippet, 'Caddyfile snippet')
    caddyfile_path = deployment / 'caddy' / 'rw' / 'Caddyfile'
    
    print(f'Reading {BOLD}{ORANGE}{snippet}{RESET}')
    with open(snippet) as f:
        snippet_contents = f.read()
    
    shared_block = f'''\
	file_server browse {{
		root /webroot
	}}

	log {{
		output file /rw/access.log {{
			mode 0644
		}}
		format json
	}}

{snippet_contents}'''
    
    print(f'Writing {BOLD}{ORANGE}{caddyfile_path}{RESET}')
    with open(caddyfile_path, 'w') as f:
        f.write(f'''\
# Autogenerated, do not modify

{{
	# Not necessary, I just don't like the admin API
	admin off

	http_port {http_port}
	https_port {https_port}

	# Required to run caddy without root/wheel
	skip_install_trust

	# Required for Quest compatibility. If OCSP stapling is left on, serving
	# files to Quest may work for up to one week, but will then fail due to
	# expiration issues. The OCSP bug can be confirmed by leaving OCSP stapling
	# on, waiting 8 days, and then running
	# `curl -v --cert-status https://HOSTNAME/`, which will end with the error
	# `curl: (91) OCSP response has expired`.
	ocsp_stapling off
	
	log {{
		format console
	}}
}}

https://{os.getenv('HOSTNAME')},
https://localhost {{
	tls /test-cert.pem /test-key.pem

{shared_block}
}}
''')
        
        if fqdn:
            f.write(f'''
https://{fqdn} {{
{shared_block}
}}
''')
    
    os.chmod(caddyfile_path, 0o664)
    
    print()

def run(deployment: pathlib.Path, user_prefix: str, session: str,
http_port: int, https_port: int, fqdn: str):
    print()
    
    if subprocess.run(f'tmux has-session -t {session}', stderr=subprocess.DEVNULL,
    shell=True).returncode == 0:
        fail(f'tmux session {BOLD}{AQUA}{session}{RESET} already in use')
    
    # Don't check to see if log *file* exists - it might not and that's fine,
    # tail -F will watch for it to be created
    for item, description in [
        (''       , 'Deployment folder'),
        ('sockets', 'Socket folder'    ),
    ]:
        verify_file(deployment / item, description)
    
    app_folders = find_app_folders(deployment)
    
    for folder in app_folders:
        app_name = folder.name
        app_ro_folder = folder / 'ro'
        app_rw_folder = folder / 'rw'
        app_sockets = deployment / 'sockets' / app_name
        
        verify_file(folder / 'ro', f'Read-only mount for {app_name}')
        verify_file(folder / 'rw', f'Read-write mount for {app_name}')
        verify_file(folder / 'image.sif', f'{app_name} image')
        
        try:
            app_user = app_sockets.owner()
        except KeyError:
            fail(f'Cannot detect user for app {BOLD}{ORANGE}{app_name}{RESET} '
                f'from ownership of socket folder {AQUA}{app_sockets}{RESET}.'
                f' Please check ownership and permissions.')
        if app_name not in app_user:
            fail(f'App name {BOLD}{ORANGE}{app_name}{RESET} not contained in '
                f'app username {BOLD}{ORANGE}{app_user}{RESET} (detected from '
                f'ownership of socket folder {AQUA}{app_sockets}{RESET} ).'
                f' Each app must have a dedicated user.')
        verify_user(app_user)
    
    caddygen(deployment, http_port, https_port, fqdn)
    
    # Caddy app needs special handling
    shellper(
        f'{ITALIC}{CYAN}Starting Caddy...',
        f'{RESET}{GRAY}tmux new-session -d -s {session} -n caddy \\\n'
        f'sudo -u {user_prefix}-caddy \\\n'
        f'apptainer run --containall '
        f'--bind {deployment / 'sockets'}:/sockets '
        f'--bind {deployment / 'caddy' / 'ro'}:/ro:ro '
        f'--bind {deployment / 'caddy' / 'rw'}:/rw:rw '
        f'--bind {deployment / 'webroot'}:/webroot:ro '
        f'{deployment / 'caddy' / 'image.sif'}{RESET}'
    )
    
    shellper(
        f'{ITALIC}{CYAN}Starting Calopr...',
        f'{RESET}{GRAY}tmux new-window -d -t {session} -n caddy-access \\\n'
        f'sudo -u {user_prefix}-caddy \\\n'
        f'apptainer exec --containall '
        f'--bind {deployment / 'caddy' / 'rw'}:/rw:rw '
        f'{deployment / 'caddy' / 'image.sif'} \\\n'
        f'sh -c \'tail -F /rw/access.log | calopr\'{RESET}'
    )
    
    for folder in app_folders:
        # Caddy app needs special handling
        if folder.name == 'caddy': continue
        
        app_name = folder.name
        app_ro_folder = folder / 'ro'
        app_rw_folder = folder / 'rw'
        app_sockets = deployment / 'sockets' / app_name
        app_user = app_sockets.owner()
        
        shellper(
            f'{ITALIC}{CYAN}Starting {app_name}...',
            f'{RESET}{GRAY}tmux new-window -d -t {session} -n {app_name} \\\n'
            f'sudo -u {app_user} \\\n'
            f'apptainer run --containall '
            f'--env HOT_RELOAD=1 '
            f'--bind {app_sockets}:/sockets '
            f'--bind {app_ro_folder}:/ro:ro '
            f'--bind {app_rw_folder}:/rw:rw '
            f'{folder / 'image.sif'}{RESET}'
        )
    
    subprocess.run(f'tmux select-window -t {session}:caddy-access',
        shell=True, check=True)
    
    print(f'{RESET}HTTP server listening at '
        f'{BLUE}https://{os.getenv('HOSTNAME')}:{https_port}{RESET} .\n'
        f'Servers running in tmux session {BOLD}{AQUA}{session}{RESET} .'
        f' Run {AQUA}tmux attach -t {BOLD}{session}{RESET} to access.\n')

def monitor(deployment: pathlib.Path, user_prefix: str, session: str):
    print()
    
    # Caddy app needs special handling
    shellper(
        f'{ITALIC}{CYAN}Watching Caddy...',
        f'{RESET}{GRAY}tmux new-session -d -s {session} -n caddy \\\n'
        f'journalctl -efu {user_prefix}-caddy.service --output cat{RESET}'
    )
    
    shellper(
        f'{ITALIC}{CYAN}Starting Calopr...',
        f'{RESET}{GRAY}tmux new-window -d -t {session} -n caddy-access \\\n'
        f'sudo -u {user_prefix}-caddy \\\n'
        f'apptainer exec --containall '
        f'--bind {deployment / 'caddy' / 'rw'}:/rw:rw '
        f'{deployment / 'caddy' / 'image.sif'} \\\n'
        f'sh -c \'tail -F /rw/access.log | calopr\'{RESET}'
    )
    
    for folder in find_app_folders(deployment):
        # Caddy app needs special handling
        if folder.name == 'caddy': continue
        
        app_name = folder.name
        
        shellper(
            f'{ITALIC}{CYAN}Watching {app_name}...',
            f'{RESET}{GRAY}tmux new-window -d -t {session} -n {app_name} \\\n'
            f'journalctl -efu {user_prefix}-{app_name}.service '
            f'--output cat{RESET}'
        )
    
    subprocess.run(f'tmux select-window -t {session}:caddy-access',
        shell=True, check=True)
    
    print(f'Loggers attached in tmux session {BOLD}{AQUA}{session}{RESET} .'
        f' Run {AQUA}tmux attach -t {BOLD}{session}{RESET} to access.\n')

###################
# Command Parsing #
###################

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(required=True)

parser_install = subparsers.add_parser('install',
    help='Install users and build apptainer images for a cluster. Will still '
    'need to be deployed before use. Idempotent')
parser_install.set_defaults(cmd=install)
parser_install.add_argument('user_prefix', type=str,
    help='Prefix for app usernames. I use the repo name')

parser_uninstall = subparsers.add_parser('uninstall',
    help='Remove users and built apptainer images for a cluster. Idempotent')
parser_uninstall.set_defaults(cmd=uninstall)
parser_uninstall.add_argument('user_prefix', type=str,
    help='Prefix for app usernames. I use the repo name')

parser_deploy = subparsers.add_parser('deploy',
    help='Build a deployment folder')
parser_deploy.set_defaults(cmd=deploy)
parser_deploy.add_argument('target', type=pathlib.Path,
    help='Location to create deployment folder at')
parser_deploy.add_argument('user_prefix', type=str,
    help='Prefix for app usernames. I use the repo name')
parser_deploy.add_argument('webroot', type=pathlib.Path,
    help='Web root to include in deployment. Will be symlinked for dev '
    'deployments, otherwise copied')
parser_deploy.add_argument('--dev', action='store_true', default=False,
    help='If true, create a dev deployment set up for hot reload')

parser_daemonize = subparsers.add_parser('daemonize',
    help='Create unit files for a deployment and add them to SystemD. Services '
    'must be started/enabled separately')
parser_daemonize.set_defaults(cmd=daemonize)
parser_daemonize.add_argument('deployment', type=pathlib.Path,
    help='Deployment folder for app cluster (see deploy subcommand)')
parser_daemonize.add_argument('user_prefix', type=str,
    help='Prefix for app usernames. I use the repo name')
parser_daemonize.add_argument('http_port', type=int)
parser_daemonize.add_argument('https_port', type=int)
parser_daemonize.add_argument('--fqdn', type=str, default='',
    help='Fully Qualified Domain Name, if applicable')

parser_clear_daemons = subparsers.add_parser('clear-daemons',
    help='Check for a daemonized deployment based on user prefix and remove it')
parser_clear_daemons.set_defaults(cmd=clear_daemons)
parser_clear_daemons.add_argument('user_prefix', type=str,
    help='Prefix for app usernames. I use the repo name')

parser_caddygen = subparsers.add_parser('caddygen',
    help='Generate a Caddyfile (used internally, exposed for debugging)')
parser_caddygen.set_defaults(cmd=caddygen)
parser_caddygen.add_argument('deployment', type=pathlib.Path,
    help='Deployment folder for app cluster (see deploy subcommand)')
parser_caddygen.add_argument('http_port', type=int)
parser_caddygen.add_argument('https_port', type=int)
parser_caddygen.add_argument('--fqdn', type=str, default='',
    help='Fully Qualified Domain Name, if applicable')

parser_run = subparsers.add_parser('run',
    help='Run a deployed app cluster in the specified tmux session')
parser_run.set_defaults(cmd=run)
parser_run.add_argument('deployment', type=pathlib.Path,
    help='Deployment folder for app cluster (see deploy subcommand)')
parser_run.add_argument('user_prefix', type=str,
    help='Prefix for app usernames. I use the repo name')
parser_run.add_argument('session', type=str,
    help='Name of tmux session to use')
parser_run.add_argument('http_port', type=int)
parser_run.add_argument('https_port', type=int)
parser_run.add_argument('--fqdn', type=str, default='',
    help='Fully Qualified Domain Name, if applicable')

parser_monitor = subparsers.add_parser('monitor',
    help='Set up a tmux session for viewing a cluster running under SystemD')
parser_monitor.set_defaults(cmd=monitor)
parser_monitor.add_argument('deployment', type=pathlib.Path,
    help='Deployment folder for app cluster (see deploy subcommand)')
parser_monitor.add_argument('user_prefix', type=str,
    help='Prefix for app usernames. I use the repo name')
parser_monitor.add_argument('session', type=str,
    help='Name of tmux session to use')

args = parser.parse_args()
cmd = args.cmd
del args.cmd
cmd(**vars(args))

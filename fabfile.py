"""
To get a list of commands use:
     fab --list

Prerequisites:
    - remote machine requires python and virtualenv, use `fab install_virtualenv` to install.
    - local machine requires `fabric`.
"""

import getpass

from fabric.api import cd, sudo, run, env, warn_only, settings, put
from fabric.context_managers import prefix

INSTALL_DIR = "/opt/getthat"
MAIN_FILE = "getthat.py"

FILES = [
    "webapp",
    "getthat.py",
    "fabfile.py",
    "requirements.txt",
    "README.md",
]

# put your IP here
env.hosts = []

# set user and password here if you don't want to enter it every time
env.user = None
env.password = None

env.user = env.user or getpass.getpass('Enter SSH username: ')
env.password = env.password or getpass.getpass('Enter SSH password: ')

# set SSH key here
env.key_filename = None    # needed for SSH


def deploy():
    """ Deploy server."""
    kill()

    sudo("mkdir " + INSTALL_DIR, warn_only=True)
    with cd(INSTALL_DIR):
        # upload all needed and only needed files
        for f in FILES:
            put(f, ".", use_sudo=True)

        # prepare virtual environment
        sudo("virtualenv .")
        with prefix('source %s/bin/activate' % INSTALL_DIR):
            sudo("pip install -r requirements.txt")

    start()


def clean():
    """ Kill server and delete related files."""
    kill()

    # remove files
    with warn_only():
        sudo("rm -rf %s/*" % INSTALL_DIR)
        sudo("rm -rf %s/.*" % INSTALL_DIR)
        sudo("rmdir %s" % INSTALL_DIR)


def kill():
    """ Kill server."""
    with settings(warn_only=True):
        sudo("kill $(ps aux | grep %s | grep -v grep | awk '{print $2}')" % MAIN_FILE)


def start():
    """ Start server."""
    with cd(INSTALL_DIR):
        with prefix('source %s/bin/activate' % INSTALL_DIR):
            sudo("nohup python %s & sleep 2; exit 0" % MAIN_FILE)


def restart():
    """ Restart server."""
    kill()
    start()


def install_virtualenv():
    """ Install virtualenv on remote machine."""
    # install pip if needed
    with cd("/tmp"):
        res = run("pip", warn_only=True)
        if res.failed:
            # install pip first
            run("curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py >get-pip.py")
            sudo("python get-pip.py")
            run("rm get-pip.py")

        sudo("pip install virtualenv")





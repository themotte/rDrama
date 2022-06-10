#!/usr/bin/env python3

import sys, subprocess, time

def _execute(command,**kwargs):
    check = kwargs.get('check',False)
    return subprocess.run(
        command,
        check = check,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

def _docker(command):
    return _execute([
        "docker-compose",
        "exec", '-T',
        "files",
        "bash", "-c", 
        ' && '.join(command)
    ])

def _running():
    command = ['docker','container','inspect','-f','{{.State.Status}}','themotte']
    result = _execute(command,check=True).stdout.strip()
    return result == "running"

def _start():
    command = ['docker-compose','up','--build','-d']
    result = _execute(command,check=True)
    time.sleep(1)
    return result

def _stop():
    command = ['docker-compose','down']
    result = _execute(command,check=True)
    time.sleep(1)
    return result

def _operation(name, command):
    # check if running and start if not
    running = _running()

    if not running:
        print("Starting containers...")
        _start()

    # run operation in docker container
    print(f"Running {name} . . .")
    result = _docker(command)
    print(result.stdout)

    if not running:
        print("Stopping containers...")
        _stop()

    return result

def run_test(*args):
    result = _operation("tests",[
        "cd service",
        "FLASK_APP=files/cli:app python3 -m flask db upgrade",
        "python3 -m pytest -s",
    ])

    sys.exit(result.returncode)

def run_migrate(*args):
    command = 'upgrade'

    if len(args) > 1:
        command = args[1]

    result = _operation(command,[
        "cd service",
        "export FLASK_APP=files/cli:app",
        f"python3 -m flask db {command}",
    ])

    sys.exit(result.returncode)

def run_help(*args):
    print("Available commands: (test|migrate|help)")
    print("Usage: './manage.py <command> [options]'")
    exit(0)

def error(message,code=1):
    print(message,file=sys.stderr)
    exit(code)

if __name__=='__main__':
    if len(sys.argv) < 2:
        error("Usage: './manage.py <command> [options]'")

    name = sys.argv[1]
    args = sys.argv[1:]

    if name == "test":
        run_test(*args)
    elif name == "migrate":
        run_migrate(*args)
    elif name == "help":
        run_help(*args)
    else:
        error("Not a command")
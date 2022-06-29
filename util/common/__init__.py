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
    result = _execute(command,check=False).stdout.strip()
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

def run_help():
    print("Available commands: (test|migrate|help)")
    print("Usage: './manage.py <command> [options]'")
    exit(0)

def error(message,code=1):
    print(message,file=sys.stderr)
    exit(code)

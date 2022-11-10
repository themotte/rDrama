import sys, subprocess, time

def _execute(command,**kwargs):
    check = kwargs.get('check', True)
    on_stdout_line = kwargs.get('on_stdout_line', None)
    on_stderr_line = kwargs.get('on_stderr_line', None)
    with subprocess.Popen(
        command,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ) as proc:
        stdout = None
        if proc.stdout:
            stdout = ''
            for line in proc.stdout:
                if on_stdout_line:
                    on_stdout_line(line)
                stdout += line

        stderr = None
        if proc.stderr:
            stderr = ''
            for line in proc.stderr:
                if on_stderr_line:
                    on_stderr_line(line)
                stderr += line

        proc.wait()
        if check and proc.returncode != 0:
            raise subprocess.CalledProcessError(
                    command,
                    proc.returncode,
                    stdout or None,
                    stderr or None
            )
        else:
            return subprocess.CompletedProcess(
                    command,
                    proc.returncode,
                    stdout or None,
                    stderr or None
            )

def _docker(command, **kwargs):
    return _execute([
        "docker-compose",
        "exec", '-T',
        "files",
        "bash", "-c", 
        ' && '.join(command)
    ], **kwargs)

def _status_single(server):
    command = ['docker', 'container', 'inspect', '-f', '{{.State.Status}}', server]
    result = _execute(command, check=False).stdout.strip()
    print(f"{server}: {result}")
    return result

# this should really be yanked out of the docker-compose somehow
_containers = ["themotte", "themotte_postgres", "themotte_redis"]

def _running():
    for container in _containers:
        if _status_single(container) != "running":
            return False

    return True

def _exited():
    for container in _containers:
        if _status_single(container) == "exited":
            return True

    return False

def _start():
    command = [
        'docker-compose',
        '-f', 'docker-compose.yml',
        '-f', 'docker-compose-operation.yml',
        'up',
        '--build',
        '-d',
    ]
    result = _execute(command)

    while not _running():
        if _exited():
            raise RuntimeError("Server exited prematurely")
        time.sleep(1)

    return result

def _stop():
    command = ['docker-compose','down']
    result = _execute(command)
    time.sleep(1)
    return result

def _operation(name, command):
    # check if running and start if not
    running = _running()

    if not running:
        print("Starting containers . . .")
        _start()

    # run operation in docker container
    print(f"Running {name} . . .")
    result = _docker(
        command,
        on_stdout_line=lambda line: print(line, end=''),
        on_stderr=lambda line: print(line, end=''),
    )

    if not running:
        print("Stopping containers . . .")
        _stop()

    return result

def run_help():
    print("Available commands: (test|migrate|help)")
    print("Usage: './manage.py <command> [options]'")
    exit(0)

def error(message,code=1):
    print(message,file=sys.stderr)
    exit(code)

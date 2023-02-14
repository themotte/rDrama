
import functools
import pprint
import subprocess
import sys
import time

def _execute(command,**kwargs):
    #print("Running:")
    #pprint.pprint(command)

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
    ] + command,
    **kwargs)

def _verify_none_exited():
    result = _execute([
            'docker-compose',
            'ps',
            '--status', 'exited',
            '-a',
            '-q',
        ]).stdout
    
    if result is not None and result.strip() != '':
        # failure! print all the diagnostics we can, first
        print(result)

        print(_execute([
            'docker-compose',
            'ps',
            '-a',
        ]).stdout)
        
        raise RuntimeError("Server exited prematurely")
    

def _start():
    print("Starting containers in operation mode . . .")
    print("  If this takes a while, it's probably building the container.")
    command = [
        'docker-compose',
        '-f', 'docker-compose.yml',
        '-f', 'docker-compose-operation.yml',
        'up',
        '--build',
        '-d',
        '--wait',
    ]
    result = _execute(command)

    _verify_none_exited()

    print("  Containers started!")

    return result

def _stop():
    # use "stop" instead of "down" to avoid killing all stored data
    command = ['docker-compose','stop']
    print("Stopping containers . . .")
    result = _execute(command)
    time.sleep(1)
    return result

def _operation(name, commands):
    # restart to make sure they're in the right mode
    _stop()

    _start()

    # prepend our upgrade, since right now we're always using it
    commands = [[
        "python3",
        "-m", "flask",
        "db", "upgrade"
    ]] + commands

    # run operations in docker container
    print(f"Running {name} . . .")
    for command in commands:
        result = _docker(
            command,
            on_stdout_line=lambda line: print(line, end=''),
            on_stderr=lambda line: print(line, end=''),
        )

    _stop()

    return result

def run_help():
    print("Available commands: (test|migrate|help)")
    print("Usage: './manage.py <command> [options]'")
    exit(0)

def error(message,code=1):
    print(message,file=sys.stderr)
    exit(code)

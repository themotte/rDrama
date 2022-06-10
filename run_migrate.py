#!/usr/bin/python3

import subprocess, time

# we want to leave the container in whatever state it currently is, so check to see if it's running
docker_inspect = subprocess.run([
            "docker",
            "container",
            "inspect",
            "-f", "{{.State.Status}}",
            "themotte",
        ],
        capture_output = True,
    ).stdout.decode("utf-8").strip()

was_running = docker_inspect == "running"

# update containers, just in case they're out of date
if was_running:
    print("Updating containers . . .")
else:
    print("Starting containers . . .")
    subprocess.run([
                "docker-compose",
                "up",
                "--build",
                "-d",
            ],
            check = True)
    time.sleep(1)

# run the migrations
print("Running migrations . . .")
result = subprocess.run([
    "docker-compose", 
    "exec", 
    "-T",
    "files", 
    "bash", "-c", 
    ' && '.join([
        "cd service",
        "export FLASK_APP=files/cli:app",
        "python3 -m flask db upgrade",
    ])
], capture_output=True)


print(f"Exit code: {result.returncode}")
print(result.stderr.decode("utf-8").strip())
print(result.stdout.decode("utf-8").strip())
# How to Install Drama Locally


## Overview

Installing Drama locally is the fastest way to get the software up and running and start tinkering under the hood.

---

## Windows

### Install Docker

Install Docker on your machine.

[Docker installation for Windows](https://docs.docker.com/docker-for-windows/install/)

### Download Drama

Download the latest release of Drama from GitHub.

[Drama Latest Release - GitHub](https://github.com/Aevann1/Drama/releases)

### PowerShell

Press shift+right click inside the code folder and run PowerShell. Then in PowerShell, run the following command:

```
docker-compose up
```

That's it! Visit `localhost` in your browser.

---

## Linux

### Install Docker

Install Docker on your machine.

[Docker installation for Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-18-04)

### Install Docker-compose

Install Docker-compose on your machine.

[Docker-compose installation for Ubuntu](https://www.digitalocean.com/community/tutorials/how-to-install-docker-compose-on-ubuntu-18-04)

### Download Drama

Navigate to `/opt`

```
cd /opt
```

then clone Drama into your machine.

```
git clone https://github.com/Drama/Drama/
```

### Run Drama

Navigate to `/opt/Drama`

```
cd /opt/Drama
```

then run this command

```
docker-compose up
```

That's it! Visit `localhost` in your browser.

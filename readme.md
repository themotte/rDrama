# Installation

## Overview

Installing Drama locally is the fastest way to get the software up and running and start tinkering under the hood.

---

## Windows

### Install Docker

Install Docker on your machine.

[Docker installation for Windows](https://docs.docker.com/docker-for-windows/install/)

### Download Drama

Download Drama into your machine by running this command.

```
git clone https://github.com/Aevann1/Drama/
```

### PowerShell

Press shift+right click inside the Drama code folder and run PowerShell. Then in PowerShell, run the following command:

```
docker-compose up
```

That's it! Visit `localhost` in your browser.

---

Optional: to configure the site settings and successsfully integrate it with the external services we use (hcaptcha, cloudflare, aws S3, discord, tenor and mailgun), please edit the variables in the docker-compose.yml file.

---

## Linux

### Download Drama

Download Drama into your machine by running this command.

```
git clone https://github.com/Aevann1/Drama/ /drama
```

### Install Drama

Navigate to `/drama`

```
cd /drama
```

then run the following command:

```
source setup
```

That's it. Visit `localhost` in your browser.

---

Optional: to configure the site settings and successsfully integrate it with the external services we use (hcaptcha, cloudflare, aws S3, discord, tenor and mailgun), please run this command and edit the variables:

```
nano /drama/docker-compose.yml
```
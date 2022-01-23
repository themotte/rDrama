[![Build status](https://travis-ci.com/ruqqus/ruqqus.svg?branch=master)](https://travis-ci.com/ruqqus) ![Snyk Vulnerabilities for GitHub Repo](https://img.shields.io/snyk/vulnerabilities/github/ruqqus/ruqqus) [![Website](https://img.shields.io/website/https/www.ruqqus.com?down_color=red&down_message=down&up_message=up)](https://www.ruqqus.com) ![GitHub language count](https://img.shields.io/github/languages/count/ruqqus/ruqqus) ![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/ruqqus/ruqqus) ![Lines of code](https://img.shields.io/tokei/lines/github/ruqqus/ruqqus) ![GitHub](https://img.shields.io/github/license/ruqqus/ruqqus) [![Discord](https://img.shields.io/discord/599258778520518676)](https://ruqqus.com/discord)

# Installation

Installing Drama locally is the fastest way to get the software up and running and start tinkering under the hood.

---

# Windows

1- Install Docker on your machine.

[Docker installation for Windows](https://docs.docker.com/docker-for-windows/install/)

2- Download Drama into your machine by running this command.

```
git clone https://github.com/Aevann1/Drama/
```

3- Press shift+right click inside the Drama code folder and run PowerShell. Then in PowerShell, run the following command:

```
docker-compose up
```

4- That's it! Visit `localhost` in your browser.

5- Optional: to change the domain from "localhost" to something else and configure the site settings, as well as integrate it with the external services the website uses, please edit the variables in the docker-compose.yml file and then restart the docker container from inside the docker app.

---

# Ubuntu

1- Download Drama into your machine by running this command.

```
git clone https://github.com/Aevann1/Drama/ /drama
```

2- Navigate to `/drama`

```
cd /drama
```

3- run the following command:

```
source setup
```

4- That's it. Visit `localhost` in your browser.


5- Optional: to change the domain from "localhost" to something else and configure the site settings, as well as integrate it with the external services the website uses, please run this command and edit the variables:

```
nano /env
```

then run `source /drama/restart` to apply the changes.

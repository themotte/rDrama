[![Build status](https://travis-ci.com/Aevann1/Drama.svg?branch=frost)](https://app.travis-ci.com/github/Aevann1/Drama) ![Snyk Vulnerabilities for GitHub Repo](https://img.shields.io/snyk/vulnerabilities/github/Aevann1/Drama) [![Website](https://img.shields.io/website/https/rdrama.net?down_color=red&down_message=down&up_message=up)](https://www.rdrama.net) ![GitHub language count](https://img.shields.io/github/languages/count/Aevann1/Drama) ![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/Aevann1/Drama) ![Lines of code](https://img.shields.io/tokei/lines/github/Aevann1/Drama) ![GitHub](https://img.shields.io/github/license/Aevann1/Drama)

# Installation

Installing Drama locally is the fastest way to get the software up and running and start tinkering under the hood.

---

# Windows

1- Install Docker on your machine.

[Docker installation for Windows](https://docs.docker.com/docker-for-windows/install/)

2- Download Drama into your machine by running this command.

```
git clone https://github.com/Aevann11/Drama/
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
git clone https://github.com/Aevann11/Drama/ /drama
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
nano /env.sh
```

then run `source /drama/restart` to apply the changes.

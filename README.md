<a id="readme-top"></a>
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![project_license][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]



<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/github_username/repo_name">
    <!-- <img src="images/logo.png" alt="Logo" width="80" height="80"> -->
  </a>

<h3 align="center">vlr-scraper</h3>

  <p align="center">
    A webscraper for vlr.gg that is focused on scraping series and event data into a database.
    <br />
    <a href="https://github.com/nebbyjammin/vlr-scraper"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/nebbyjammin/vlr-scraper">View Demo</a>
    &middot;
    <a href="https://github.com/nebbyjammin/vlr-scraper/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://github.com/nebbyjammin/vlr-scraper/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Setup</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

<!-- [![Product Name Screen Shot][product-screenshot]](https://example.com) -->

<p align="right">(<a href="#readme-top">back to top</a>)</p>

A webscraper for vlr.gg that is focused on scraping both historical/upcoming series and event data into a database. There are other vlr.gg webscrapers, such as [axsddlr/vlrggapi](https://github.com/axsddlr/vlrggapi) and [liulalemx/vlrgg-api](https://github.com/liulalemx/vlrgg-api) that wrap common queries for rankings, teams, events etc. in REST API endpoints. These are extremely solid options especially if you don't need rich querying. I highly recommend you check these out.

This repository contains the scraper script, which handles all the logic and scheduling of scraping series, event, match and team data. At regular intervals, the scraper inserts the scraped data into a postgres database (see [nebbyjammin/pgvlr](https://github.com/nebbyjammin/pgvlr)). A benefit of separating the REST endpoints and the scraper script is that you can hook up other APIs if you want custom querying and overall finer control over the data. Of course, the downsides of this approach is having the risk of slightly outdated data. Recent (within the last week)/Upcoming events and matches are scraped every 3-10 minutes, and new series are scanned for every day. Historical data is scraped periodically depending on how long ago it was last scraped, ranging anywhere between every week to every 6 months. This is a tradeoff that had to be made when taking this approach, since scraping the entire vlr.gg website every day is costly and slow, so we take the risk that historical data is extremely unlikely to change (especially for vlr.gg) and scrape recent pages more frequently.

At the moment, player data is not available for this API - as I don't really have a strong need to store/use player data at the moment, but will accept pull requests if anyone wants to implement them :).  However, I do not plan on including functionality for forums as I want this project to be exclusively focused on scraping VLR match and event data. If you are looking for this sort of functionality, I strongly suggest checking out these repositories I mentioned before: [axsddlr/vlrggapi](https://github.com/axsddlr/vlrggapi) and [liulalemx/vlrgg-api](https://github.com/liulalemx/vlrgg-api)

### Built With

* [![Python][Python]][Python-url]
* [![Docker][Docker]][Docker-url]
* [![Postgres][Postgres]][Postgres-url]
* [![Telegram][Telegram]][Telegram-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

First, ensure Python, pip, and Docker are installed, and set up a Python virtual environment for dependencies.

### Prerequisites



#### 1. Set up Docker

Install Docker for your operating system:

- **Windows/macOS:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux:** [Install Docker Engine on Linux](https://docs.docker.com/engine/install/)

After installation, verify Docker is running:
```sh
docker --version
```

Refer to the [Docker Get Started Guide](https://docs.docker.com/get-started/) for more help.

### Setup

Here is the setup if you just want to run the container and start scraping. If you want to just test locally without an ssh tunnel, you can run the code normally outside of the container (see 4).

#### 1. Clone the repo
```sh
git clone https://github.com/nebbyjammin/vlr-scraper.git
```
#### 2. Create a file `prod.env` at project root.
> **NOTE:** The scraper script uses `autossh` to initialise an ssh tunnel, forwarding `$LOCAL_PORT` to `$API_PORT`.

Refer to `.env.example` as a reference. Enter credentials and any other configuration options.

> **NOTE:** In development mode (when running without the docker container), the scraper will use `.env` instead of `prod.env` which is used when the project is containerised.

#### 3. Add private key file named `id_ed25519` into `.ssh/` directory.
Copy an authorised private key at path `.ssh/id_ed25519`. This key will be used to create an SSH tunnel to the private API. Also create an empty `known_hosts` file at path `.ssh/known_hosts`. Feel free to add authorised hosts to increase security.
    
#### 4. [Optional] Change git remote url to avoid accidental pushes to base project
```sh
git remote set-url origin github_username/repo_name
git remote -v # confirm the changes
```
#### 5. Setup the Postgres database + backend api using [nebbyjammin/pgvlr](https://github.com/nebbyjammin/pgvlr)
---
See the `README.md` setup guide for https://github.com/nebbyjammin/pgvlr. Set this up in a different directory - **it is recommended to set this up on a virtual private server, separate from this script if you intend on hooking up your own backend to the database.**

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## Usage

Once you have `prod.env` (or `.env` if you are running outside of the container) set up, as well as the private key file, you are now ready to run the script for the first time.

#### 1. Build series
---
You can think of series as valorant 'leagues', where they have one or more events. The first step of scraping our data is to recursively scrape series data. By doing this, we gather 99% of all the data required (Scrape series, then events, then matches, then teams).

While in the root directory, run the script for the first time with this command:

##### Windows (batch script)
```bat
.\docker-up-build-series.bat
```

##### Linux (bash script)
```sh
./docker-up-build-series.sh
```

##### Raw docker-compose
```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  -f docker-compose.build-series.yml up -d --build
```

This will create a docker image and run the container with the correct flags (that being `--build-series`). If you are running this outside of a docker container, run `python main.py --build-series`.

**NOTE:** This process can take quite a long time (allow at least 24 hours). You will know when the process is complete when you see in the console:

```sh
Sending task scheduler heartbeat...
Estimated size of task queue is 0 # No more tasks to scrape.
```

Alternative, you can type in a TTY:

```sh
# You must be in a TTY environment, it is not possible to run this command in a docker container.
scheduler qsize # or sched size
```

#### 2. Build event
---
Most events belong to a parent series, which should have been recursively scraped in the above steps. However, there are some events that do not belong to any series (mostly offseason events).

While in the root directory, follow these steps by executing these commands:

##### Step A — Shutdown docker container
```sh
docker compose down # Stop docker container.
```

##### Step B — Restart the docker container with `--build-events`

###### Windows (batch script)
```bat
.\docker-up-build-events.bat
```

###### Linux (bash script)
```sh
./docker-up-build-events.sh
```

###### Raw docker-compose
```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  -f docker-compose.build-events.yml up -d --build
```

**NOTE:** `--build-flag` is probably optional, but is just here to ensure the container is rebuilt.

After executing these commands, allow the scraper to scrape the events. This will take a while as well. Allow up to 2 hours.

You will know when the process is complete when you see in the console:

```sh
Sending task scheduler heartbeat...
Estimated size of task queue is 0 # No more tasks to scrape.
```

Alternative, you can type in a TTY:

```sh
# You must be in a TTY environment, it is not possible to run this command in a docker container.
scheduler qsize # or sched size
```

#### 3. Run normally to maintain integrity and validity of data
---
Now that we have scraped all the historical data, we can now run the program and let it scrape new data / update old data. The program automatically handles scheduling rescrapes / discovering new data, so don't worry about that.

While in the root directory, run the following commands:

##### Step A — Shutdown docker container
```sh
docker compose down # Stop the docker container
```

##### Step B — Restart the docker container with no flags

###### Windows (batch script)
```bat
.\docker-up.bat
```

###### Linux (bash script)
```sh
./docker-up.sh
```

###### Raw docker-compose
```sh
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
   up -d --build
```

**NOTE:** `--build-flag` is probably optional, but is just here to ensure the container is rebuilt.

The scraper will now ensure that the entries in the database stay updated when new events pop up AND will update any old entries, in the case that any of those get updated.

---

<p align="right">(<a href="#readme-top">back to top</a>)</p>

4. Using commands within the program:
While the program is running, you can execute a list of commands.
<!-- TODO: Implement this -->

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
See the [open issues](https://github.com/nebbyJammin/vlr-scraper/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Top contributors:

<a href="https://github.com/github_username/repo_name/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=github_username/repo_name" alt="contrib.rocks image" />
</a>



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.md` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
<!-- CONTACT -->
## Contact

Benjamin Nguyen - [@twitter_handle](https://twitter.com/twitter_handle) - email@email_client.com

Project Link: [https://github.com/nebbyJammin/vlr-scraper](https://github.com/nebbyJammin/vlr-scraper)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/github_username/repo_name.svg?style=for-the-badge
[contributors-url]: https://github.com/nebbyJammin/vlr-scraper/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/nebbyJammin/vlr-scraper.svg?style=for-the-badge
[forks-url]: https://github.com/nebbyJammin/vlr-scraper/network/members
[stars-shield]: https://img.shields.io/github/stars/nebbyJammin/vlr-scraper.svg?style=for-the-badge
[stars-url]: https://github.com/nebbyJammin/vlr-scraper/stargazers
[issues-shield]: https://img.shields.io/github/issues/nebbyJammin/vlr-scraper.svg?style=for-the-badge
[issues-url]: https://github.com/nebbyJammin/vlr-scraper/issues
[license-shield]: https://img.shields.io/github/license/nebbyJammin/vlr-scraper.svg?style=for-the-badge
[license-url]: https://github.com/nebbyJammin/vlr-scraper/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/linkedin_username
[product-screenshot]: images/screenshot.png

<!-- Shields.io badges. You can a comprehensive list with many more badges at: https://github.com/inttter/md-badges -->
[Python]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=fff
[Python-url]: https://www.python.org

[Docker]: https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=fff
[Docker-url]: https://www.docker.com

[Postgres]: https://img.shields.io/badge/Postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white
[Postgres-url]: https://www.postgresql.org

[Telegram]: https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white
[Telegram-url]: https://telegram.org
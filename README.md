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
    <img src="images/logo.png" alt="Logo" width="80" height="80">
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
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

[![Product Name Screen Shot][product-screenshot]](https://example.com)



<p align="right">(<a href="#readme-top">back to top</a>)</p>

A webscraper for vlr.gg that is focused on scraping series and event data into a database. There are other vlr.gg webscrapers, such as [axsddlr/vlrggapi](https://github.com/axsddlr/vlrggapi) and [liulalemx/vlrgg-api](https://github.com/liulalemx/vlrgg-api) that wrap common queries for rankings, teams, events etc. in REST API endpoints. These are extremely solid options especially if you don't need rich querying.

This repository contains the scraper script, which handles all the logic and scheduling of scraping series, event, match and team data. At regular intervals, the scraper inserts the scraped data into a postgreSQL database (see [nebbyjammin/pgvlr](https://github.com/nebbyjammin/pgvlr)). A benefit of separating the REST endpoints and the scraper script is that you can hook up other APIs if you want custom querying and overall finer control over the data.

At the moment, player data is not available for this API - as I don't really have a strong need to store/use player data at the moment, but will accept pull requests if anyone wants to implement them :).

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

1. Clone the repo
   ```sh
   git clone https://github.com/nebbyjammin/vlr-scraper.git
   ```
2. Create a file `prod.env` at project root.
    > **NOTE:** The scraper script uses `autossh` to initialise an ssh tunnel, forwarding `$LOCAL_PORT` to `$API_PORT`.

    Refer to `.env.example` as a reference. Enter credentials and any other configuration options.

    > **NOTE:** In development mode (when running without the docker container), the scraper will use `.env` instead of `prod.env` which is used when the project is containerised.

3. Add private key file named `id_ed25519` into `.ssh/` directory.
    Copy an authorised private key at path `.ssh/id_ed25519`. This key will be used to create an SSH tunnel to the private API. Also create an empty `known_hosts` file at path `.ssh/known_hosts`. Feel free to add authorised hosts to increase security.
    
4. **[Optional]** Change git remote url to avoid accidental pushes to base project
   ```sh
   git remote set-url origin github_username/repo_name
   git remote -v # confirm the changes
   ```
5. **Setup the postgreSQL database + backend api using [nebbyjammin/pgvlr](https://github.com/nebbyjammin/pgvlr)**
    See the `README.md` setup guide for https://github.com/nebbyjammin/pgvlr. Set this up in a different directory - **it is recommended to set this up on a virtual private server, separate from this script if you intend on hooking up your own backend to the database.**

<p align="right">(<a href="#readme-top">back to top</a>)</p>



## Usage

Once you have `prod.env` (or `.env` if you are running outside of the container) setup, as well as the private key file, you are now ready to run the script for the first time.

1. Build series
You can think of series as valorant 'leagues', where they have one or more events. The first step of scraping our data is to recursively scrape series data. By doing this, we gather 99% of all the data required (Scrape series, then events, then matches, then teams).<br>
While in the root directory, run the script for the first time with this command:
    - **Windows:** Run docker script using batch script.
        ```bat
        .\docker-up-build-series.bat
        ```
    - **Linux:** Run docker script using bash script.
        ```sh
        ./docker-up-build-series.sh
        ```
    - **Other:**
        ```sh
        docker compose -f docker-compose.yml -f docker-compose.prod.yml \
            -f docker-compose.build-series.yml up -d --build
        ```
    This will create a docker image and run the container with the correct flags (that being `--build-series`). If you are running this outside of a docker container, run `python main.py --build-series`.

2. B

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [ ] Feature 1
- [ ] Feature 2
- [ ] Feature 3
    - [ ] Nested Feature

See the [open issues](https://github.com/github_username/repo_name/issues) for a full list of proposed features (and known issues).

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

Distributed under the project_license. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Your Name - [@twitter_handle](https://twitter.com/twitter_handle) - email@email_client.com

Project Link: [https://github.com/github_username/repo_name](https://github.com/github_username/repo_name)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* []()
* []()
* []()

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/github_username/repo_name.svg?style=for-the-badge
[contributors-url]: https://github.com/github_username/repo_name/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/github_username/repo_name.svg?style=for-the-badge
[forks-url]: https://github.com/github_username/repo_name/network/members
[stars-shield]: https://img.shields.io/github/stars/github_username/repo_name.svg?style=for-the-badge
[stars-url]: https://github.com/github_username/repo_name/stargazers
[issues-shield]: https://img.shields.io/github/issues/github_username/repo_name.svg?style=for-the-badge
[issues-url]: https://github.com/github_username/repo_name/issues
[license-shield]: https://img.shields.io/github/license/github_username/repo_name.svg?style=for-the-badge
[license-url]: https://github.com/github_username/repo_name/blob/master/LICENSE.txt
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


[Next.js]: https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white
[Next-url]: https://nextjs.org/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[Vue.js]: https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D
[Vue-url]: https://vuejs.org/
[Angular.io]: https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white
[Angular-url]: https://angular.io/
[Svelte.dev]: https://img.shields.io/badge/Svelte-4A4A55?style=for-the-badge&logo=svelte&logoColor=FF3E00
[Svelte-url]: https://svelte.dev/
[Laravel.com]: https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white
[Laravel-url]: https://laravel.com
[Bootstrap.com]: https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white
[Bootstrap-url]: https://getbootstrap.com
[JQuery.com]: https://img.shields.io/badge/jQuery-0769AD?style=for-the-badge&logo=jquery&logoColor=white
[JQuery-url]: https://jquery.com 
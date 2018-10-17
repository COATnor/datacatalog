# nina-ckan-coat

[![pipeline status](https://gitlab.com/nina-data/nina-ckan-coat/badges/master/pipeline.svg)](https://gitlab.com/nina-data/nina-ckan-coat/commits/master)

## Description

[NINA](https://www.nina.no/) [CKAN](https://ckan.org/) catalogue for the [COAT](https://www.coat.no/) project.
It is a customized distribution of CKAN which includes the [ckanext-coat extension](https://gitlab.com/nina-data/ckanext-coat).

It uses the tools provided by the [nina-data/tools](https://gitlab.com/nina-data/tools) repository.

## Requirements

All the tools and scripts in this file have been developed and tested on GNU/Linux systems only.

Dependencies:
  - Python 3.6+
  - Make
  - Docker
  - Portainer (optional)

If the dependencies are met, but `python3 -V` shows an incompatible version, please export the `PYTHON` variable like this:

```bash
export PYTHON="python3.6"
```

## Development

```bash
$ make prepare # dev only
$ make
$ (cd output/dev && docker-compose up --build)
```

The `--build` option forces `docker-compose` to build the image locally instead of fetching it from the Docker Registry.

Please stop the containers before running `make` again. Use `CTRL+C` to stop them.

Changes made inside the `ckanext-coat` directory will affect the running container.

The credentials for the development image are:
  - Username: administrator
  - Password: administrator

### Debugging

Add this line before the Python code you would like to debug:

`import pdb; pdb.set_trace()`

Attach to the CKAN container:

`$ docker attach ckan`

Interact with the CKAN in order to break into the Python debugger.

## Deployment

```bash
$ make
$ (cd output/deploy && docker-compose up --detach)
```

The `--detach` option run containers in the background.

Please stop the containers before running `make` again. To stop them run:

```bash
$ (cd output/deploy && docker-compose stop)
```

## LDAP login

Export `LDAP_PASSWORD` to activate NINA LDAP.

## Portainer

If you want to deploy on Portainer, export `PORTAINER_USERNAME` and `PORTAINER_PASSWORD` and run:

```bash
$ make deploy PROJECT="output/deploy" NAME="ninackancoat" SERVER="http://localhost:9000"
```

## Providing initial data

Ìf you want to provide initial data to CKAN, export `CKAN_API_KEY` (available on your user profile) and run:

```bash
$ make populate SERVER="http://localhost:5000"
```

## Security

Do not store secrets in Bash history: check if `HISTCONTROL` is set to `ignorespace` or `ignoreboth` in your `.bashrc` file.

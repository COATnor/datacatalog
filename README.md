# nina-ckan-coat

[![pipeline status](https://gitlab.com/nina-data/nina-ckan-coat/badges/master/pipeline.svg)](https://gitlab.com/nina-data/nina-ckan-coat/commits/master)

## Description

[NINA](https://www.nina.no/) [CKAN](https://ckan.org/) catalogue for the [COAT](https://www.coat.no/) project.
It is a customized distribution of CKAN which includes the [ckanext-coat extension](https://gitlab.com/nina-data/ckanext-coat).

## Requirements

All the tools and scripts in this file have been developed and tested on GNU/Linux systems only.

Dependencies:
  - Python 3.8+
  - Earthly
  - Docker

## Development/debugging

- Build: `earthly +container`
- Copy `testing.env` to `.env` and set `DOI_*` test variables
- Run: `docker compose --profile dev run --rm --service-ports ckan-dev`

### Testing

```bash
earthly +container-test
docker compose --profile test down -v
docker compose --profile test run --rm test
```

## Deployment

1. Copy `template.env` to `.env`
2. Set `DOI_*` variables
3. Set `CKAN_OAUTH2_*` variables

## Common commands

Create a new user:
```bash
docker compose exec ckan ckan -c /etc/ckan/production.ini sysadmin add $USER
```

## Security

Do not store secrets in Bash history: check if `HISTCONTROL` is set to `ignorespace` or `ignoreboth` in your `.bashrc` file.

## Non-upstreamed changed

- ckanext-oauth2
  - PR for Python 3/CKAN 2.9 is stale: https://github.com/conwetlab/ckanext-oauth2/pull/42
- ckanext-scheming
  - A custom patch is used to skip validation on the parent datasets; the discussion is still ongoing: https://github.com/ckan/ckanext-scheming/issues/331

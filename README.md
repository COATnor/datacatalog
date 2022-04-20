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

## Development

- Build: `earthly +container`
- Copy `testing.env` to `.env` and set `DOI_*` test variables
- Run: `docker compose run ckan`
- Stop: `docker compose down`

### Debugging

Uncomment `pdb` section in `docker-compose.yml` and start CKAN.

### Testing

```bash
docker compose -f docker-compose.yml -f tests/docker-compose.yml run test
```

## Deployment

1. Copy `testing.env` to `.env`
2. Set `MODE` to `prod`
3. Set `DOI_*` variables to production values
4. Set `CKAN_OAUTH2_*` variables
5. Remove `./ckanext` as mount point

## Common commands

Create a new user:
```bash
docker compose exec ckan ckan -c /etc/ckan/production.ini sysadmin add $USER
```

## Security

Do not store secrets in Bash history: check if `HISTCONTROL` is set to `ignorespace` or `ignoreboth` in your `.bashrc` file.

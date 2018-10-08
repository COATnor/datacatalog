# nina-ckan-coat

[![pipeline status](https://gitlab.com/nina-data/nina-ckan-coat/badges/master/pipeline.svg)](https://gitlab.com/nina-data/nina-ckan-coat/commits/master)

## Description

[NINA](https://www.nina.no/) [CKAN](https://ckan.org/) catalogue for [COAT](https://www.coat.no/) project.
It is a customized distribution of CKAN which includes the [ckanext-coat extension](https://gitlab.com/nina-data/ckanext-coat).

`make` launches `dockerfiles-generator.py` to generate an `output` directory containing a directory for each target.

## Usage

Requirements:
  - Docker
  - Python 3.6+
  - Make

### Development

```bash
$ make
$ make prepare # dev only
$ cd output/dev
$ docker-compose up --build
```

Changes made under the `ckanext-coat` directory will affect the running container.

### Deployment

```bash
$ make
$ cd output/deploy
$ docker-compose up # image from registry
```

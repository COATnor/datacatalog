# How to produce Docker images

`make` is used to generate Docker files via `dockerfiles-generator.py`:

```
$ make
```

An `output` directory is generated, containing a directory for each target.

## Development image

```
$ cd output/dev
$ docker-compose up --build
```

## Deployment image

```
$ cd output/deploy
$ docker build -t registry.gitlab.com/nina-data/nina-ckan-test .
$ docker-compose up
```



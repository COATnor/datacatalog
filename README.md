# nina-ckan-coat

`make` is used to generate Docker files via `dockerfiles-generator.py`:

```
$ make
```

An `output` directory is generated, containing a directory for each target.

## Development

```
$ cd output/dev
$ docker-compose up --build
```

## Deployment

```
$ cd output/deploy
$ docker-compose up
```



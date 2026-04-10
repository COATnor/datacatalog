The goal of coat2pycsw is to achieve interoperability with the SIOS Data Access Portal by following the [Interoperability Guidelines for the SIOS Data Management System (SDMS)](https://github.com/SIOS-Svalbard/SDMSInteroperabilityGuidelines).

coat2pycsw reads data from [data.coat.no](https://data.coat.no) using the CKAN API, generates ISO-19115/ISO-19139 metadata using [pygeometa](https://geopython.github.io/pygeometa/), and populates a [pycsw](https://pycsw.org/) instance which exposes the metadata via CSW, OAI-PMH and OGC Records API.

## Architecture

Two containers share a SQLite database via a named volume:

- pycsw; official `geopython/pycsw` image serving the catalogue
- coat2pycsw: index CKAN datasets into pycsw


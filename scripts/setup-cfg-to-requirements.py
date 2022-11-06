#!/usr/bin/env python3

import configparser
import sys

path = sys.argv[1]
config = configparser.ConfigParser()
config.read(path)
print(config['options']['install_requires'].strip())

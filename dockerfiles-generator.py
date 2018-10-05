#!/usr/bin/env python3

import jinja2 # fades
import yaml # fades

import argparse
import os

parser = argparse.ArgumentParser(description="Genetare Docker files from Jinja templates")
parser.add_argument('--settings', default='settings.yaml', help="Variables for the templates")
parser.add_argument('--templates', default='templates', help="Templates directory")
parser.add_argument('--output', default='output', help="Output directory")
parser.add_argument('targets', metavar='target', nargs='*', default=['dev', 'deploy'],help="Targets")
args = parser.parse_args()
conf = yaml.load(open(args.settings))

environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(args.templates),
    trim_blocks=True,
    lstrip_blocks=True,
)

for filename in os.listdir(args.templates):
    path = os.path.join(args.templates, filename)
    if os.path.isdir(path) or os.path.islink(path):
        continue
    print(f"Fetching template file {filename}...")
    try:
        template = environment.get_template(filename)
    except UnicodeDecodeError:
        print(f"Could not read {filename}. File skipped.")
    for target in args.targets:
        target_dir = os.path.join(args.output, target)
        os.makedirs(target_dir, exist_ok=True)
        print(f"Generating {filename} for target \"{target}\"...")
        with open(os.path.join(target_dir, filename), 'w') as output:
            output.write(template.render(target=target, extensions=conf))

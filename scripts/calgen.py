#!/usr/bin/python3

"""Script to generate the calendar from protoype calcalc calendar."""

import re
import sys

import yaml


def make_descriptors(calcalc_lines):
    # Descriptors plural, because there could be multiple, separated by blank
    # lines, but currently we just handle the first.
    desc = {}
    if calcalc_lines:
        desc['titulus'] = re.sub(r'\W', '-', calcalc_lines.pop(0).lower())
    if calcalc_lines:
        if calcalc_lines[0].endswith('IV. classis'):
            desc['classis'] = 4
        elif calcalc_lines[0].endswith('III. classis'):
            desc['classis'] = 3
        elif calcalc_lines[0].endswith('II. classis'):
            desc['classis'] = 2
        elif calcalc_lines[0].endswith('I. classis'):
            desc['classis'] = 1
    return [desc]


def parse(f):
    raw = {}
    # Completely spurious parser, but good enough.
    for line in f:
        line = line.rstrip()
        print(line, file=sys.stderr)
        m = re.match(r'\[(.*)\].*1960', line)
        if not m:
            m = re.match(r'\[(.*)\]$', line)
        if m:
            section = raw['calendarium/' + m.group(1)] = []
            continue
        if not '=' in line:
            section.append(line)

    return {k: make_descriptors(v) for (k, v) in raw.items()}


def main():
    with open(sys.argv[1], 'r') as f:
        print(yaml.dump(parse(f)))


if __name__ == '__main__':
    main()


#!/usr/bin/python3

"""Script to demonstrate some sign of life."""

# Run with PYTHONPATH=src:tests/officium

import argparse

import yaml

import flat_test_data
from officium.calendar import CalendarResolver, Date
from officium.offices import SundayAfterPentecostOffice
from officium.parts import Text
from officium.vespers import Vespers

def render(things):
    for thing in things:
        if isinstance(thing, Text):
            print(thing.render())
        else:
            render(thing.resolve())

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--datafile')
    parser.add_argument('date', nargs='?')
    return parser.parse_args()

def main(options):
    try:
        date = Date(*(int(x) for x in options.date.split('-')))
    except:
        date = Date(2020, 8, 23)
    if options.datafile:
        with open(options.datafile) as f:
            flat_test_data.generic.update(yaml.safe_load(f))
    resolver = CalendarResolver(flat_test_data.generic)
    offices = resolver.offices(date, calendar=None)
    for office in offices:
        print(office._office)
        print(office._occurring)
        print(office._concurring)
    render(offices)

if __name__ == '__main__':
    main(parse_args())

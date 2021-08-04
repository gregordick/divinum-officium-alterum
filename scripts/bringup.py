#!/usr/bin/python3

"""Script to demonstrate some sign of life."""

import argparse

from officium.bringup import bringup_components, make_date, resolvers
from officium.parts import Antiphon, StructuredLookup, Versicle, VersicleResponse, Psalmody


def render_one(thing):
    if isinstance(thing, Antiphon):
        print("Ant. ", end='')
    if isinstance(thing, Versicle):
        print("V. ", end='')
    elif isinstance(thing, VersicleResponse):
        print("R. ", end='')
    elif isinstance(thing, str):
        print(thing)


def render(things, lang_data):
    for thing in things:
        render_one(thing)
        if not isinstance(thing, str):
            try:
                children = thing.resolve()
                render(children, lang_data)
            except TypeError:
                if lang_data:
                    render(thing.resolve(lang_data), lang_data)
                else:
                    render_one(repr(thing))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rubrics', '-r', choices=resolvers.keys(),
                        default='rubricarum')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('generic_file')
    parser.add_argument('lang_data_file')
    parser.add_argument('date')
    return parser.parse_args()


def main():
    options = parse_args()

    resolver, lang_data = bringup_components(options.generic_file,
                                             options.lang_data_file,
                                             options.rubrics)

    date = make_date(options.date)
    current_date = date #- 366
    resolver._resolve_transfer_cache = resolver.resolve_transfer(current_date, date + 1)
    resolver._resolve_transfer_cache_base = current_date

    while current_date <= date:
        offices = resolver.offices(current_date)
        if options.verbose or current_date == date:
            for office in offices:
                print("Office:", office._office)
                print("Commemorations:", office._commemorations)
                print("Concurring:", office._concurring)
            render(offices, lang_data)
        current_date += 1


if __name__ == '__main__':
    main()

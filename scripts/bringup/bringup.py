#!/usr/bin/env python3

"""Script to demonstrate some sign of life."""

import argparse

from officium.bringup import bringup_components, make_date, resolvers
from officium.parts import Antiphon, StructuredLookup, Versicle, VersicleResponse, Psalmody
from officium.vespers import Vespers


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
            except TypeError:
                if lang_data:
                    render(thing.resolve(lang_data), lang_data)
                else:
                    render_one(repr(thing))
            else:
                render(children, lang_data)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rubrics', '-r', choices=resolvers.keys(),
                        default='rubricarum')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--titular-path', '-t')
    parser.add_argument('--hour')
    parser.add_argument('generic_file')
    parser.add_argument('lang_data_file')
    parser.add_argument('date')
    parser.add_argument('end_date', nargs='?')
    return parser.parse_args()


def main():
    options = parse_args()

    resolver, lang_data = bringup_components(options.generic_file,
                                             options.lang_data_file,
                                             options.rubrics,
                                             options.titular_path)

    current_date = make_date(options.date)
    end_date = make_date(options.end_date or options.date)
    resolver._resolve_transfer_cache = resolver.resolve_transfer(current_date, end_date + 1)
    resolver._resolve_transfer_cache_base = current_date

    while current_date <= end_date:
        hours = resolver.offices(current_date).items()
        if options.hour is not None:
            hours = ((name, offices) for (name, offices) in hours
                     if name == options.hour)
        for (_, offices) in hours:
            if options.verbose or current_date == end_date:
                print("Date:", current_date)
                for office in offices:
                    print("Office:", office, office._office)
                    print("Commemorations:", office._commemorations)
                    if isinstance(office, Vespers):
                        print("Concurring:", office._concurring)
            render(offices, lang_data if options.render else None)
        current_date += 1


if __name__ == '__main__':
    main()

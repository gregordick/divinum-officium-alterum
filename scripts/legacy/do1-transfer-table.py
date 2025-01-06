#!/usr/bin/env python3

"""Generate a transfer table for the specified year for use with the original
Perl implementation of Divinum Officium.
"""

import argparse

from officium.bringup import bringup_components, make_date, resolvers
from officium.calendar import Date


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', '-a', action='store_true')
    parser.add_argument('--rubrics', '-r', choices=resolvers.keys(),
                        default='rubricarum')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('generic_file')
    parser.add_argument('lang_data_file')
    parser.add_argument('year', type=int, help="Year to generate.")
    return parser.parse_args()


def main():
    options = parse_args()

    resolver, lang_data = bringup_components(options.generic_file,
                                             options.lang_data_file,
                                             options.rubrics,
                                             titular_path=None)

    current_date = Date(options.year, 1, 1)
    end_date = Date(options.year, 12, 31)
    resolver._resolve_transfer_cache = resolver.resolve_transfer(current_date, end_date + 1)
    resolver._resolve_transfer_cache_base = current_date

    while current_date <= end_date:
        offices = resolver.offices(current_date)['lauds']
        natural_office = resolver.resolve_occurrence(current_date)[0]
        for office in offices:
            # XXX: Hacky test for equality of offices.
            if options.all or list(office._office.keys) != list(natural_office.keys):
                if options.verbose:
                    print("Date:", current_date)
                    print("Office:", office._office)
                    print("Commemorations:", office._commemorations)
                print(f'{current_date.month:02}-{current_date.day:02}={office._office.desc.get("do_basename")}')
        current_date += 1


if __name__ == '__main__':
    main()

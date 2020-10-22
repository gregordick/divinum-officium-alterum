#!/usr/bin/python3

"""Generate a transfer table for the specified year for use with the original
Perl implementation of Divinum Officium.
"""

import argparse

import officium.calendar


def parse_command_line():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('year', type=int, help="Year to generate.")
    return parser.parse_args()


def main(options):
    easter = officium.calendar.CalendarResolver.easter_sunday(options.year)
    print("Easter %d falls on %s" % (options.year, easter))


if __name__ == '__main__':
    main(parse_command_line())

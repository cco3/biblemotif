#!/usr/bin/env python3
#
# This script is for parsing a strong's greek dictionary into rows of json
# objects.
#
# You can get the xml from here:
# https://raw.githubusercontent.com/morphgnt/strongs-dictionary-xml/master/strongsgreek.xml
#
import argparse
import collections
import sys
import time

import pysblgnt


class Timer:
    def __init__(self, start_text):
        self.start_text = start_text

    def __enter__(self):
        self.start = time.clock()
        print('{}...'.format(self.start_text), end='')
        sys.stdout.flush()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start
        print('{:0.2f} seconds'.format(self.interval))


def get_freq_map():
    """Create a frequency map out of the new testament
    The first level of keys is the book number, where
    * 0 represents all books
    * 1 represents Mat
    * 27 represents Rev

    The second level of keys is the lexical form of the term

    """
    freq_map = collections.defaultdict(collections.Counter)
    for i in range(27):
        for row in pysblgnt.morphgnt_rows(i + 1):
            freq_map[0][row['lemma']] += 1
            freq_map[i][row['lemma']] += 1
    return freq_map


def main():
    """The main routine."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Parse qev.txt and output to '
                                     'multiple json files')
    args = parser.parse_args()

    with Timer('Counting words in the NT'):
        freq_map = get_freq_map()

    return 0


if __name__ == '__main__':
    try:
        exit(main())
    except KeyboardInterrupt:
        print('Exiting due to KeyboardInterrupt!', file=sys.stderr)

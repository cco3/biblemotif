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
import math
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


def calc_freqs(data):
    """Create a frequency map out of the new testament

    freqs
        key: lexical form of word
        value: frequency count

    """
    all_books = data[0]
    all_books['freqs'] = collections.Counter()
    for i in range(27):
        book = data[i + 1]
        book['freqs'] = collections.Counter()
        for row in pysblgnt.morphgnt_rows(i + 1):
            all_books['freqs'][row['lemma']] += 1
            book['freqs'][row['lemma']] += 1


def calc_atfs(data):
    r"""Get augmented term frequencies

    atf = \log{2}{\frac{tf}{max_tf}}

    freqs
        key: lexical form of word
        value: augmented term frequency

    """
    for book in data:
        book['atfs'] = collections.defaultdict(collections.Counter)
        freqs = book['freqs']
        _, max_freq = freqs.most_common(1)[0]
        for lex, freq in freqs.items():
            book['atfs'][lex] = math.log2(freq / max_freq)



def main():
    """The main routine."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Parse qev.txt and output to '
                                     'multiple json files')
    args = parser.parse_args()

    # This data structure stores all our calculations
    # The first level of keys is the book number, where
    # * 0 represents all books
    # * 1 represents Mat
    # * 27 represents Rev
    # The second level of keys are the various types of data for that book
    # e.g. freqs, maxfreq, etc.
    data = [{} for i in range(28)]
    with Timer('Counting words in the NT'):
        calc_freqs(data)
    with Timer('Calculating augmented term frequencies'):
        calc_atfs(data)

    return 0


if __name__ == '__main__':
    try:
        exit(main())
    except KeyboardInterrupt:
        print('Exiting due to KeyboardInterrupt!', file=sys.stderr)

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
import statistics
import sys
import time

import pysblgnt

BOOKS = [
    'All',
    'Mat',
    'Mar',
    'Luk',
    'Joh',
    'Act',
    'Rom',
    '1Co',
    '2Co',
    'Gal',
    'Eph',
    'Php',
    'Col',
    '1Th',
    '2Th',
    '1Ti',
    '2Ti',
    'Tit',
    'Phm',
    'Heb',
    'Jam',
    '1Pe',
    '2Pe',
    '1Jo',
    '2Jo',
    '3Jo',
    'Jde',
    'Rev',
]


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


class TDefTerm:
    def __init__(self, line):
        split_line = line.split(':')
        self.lex = split_line[0]
        self.attrs = ''
        if len(split_line) > 1:
            self.attrs = split_line[1]

    def matches(self, row):
        if self.lex == '*':
            return True
        if self.lex != row['lemma']:
            return False
        if 'G' in self.attrs and row['ccat-parse'][4] != 'G':
            return False
        return True
                


class TDef:
    def __init__(self, line):
        self.terms = []
        for term in line.split():
            self.terms.append(TDefTerm(term))

    def __len__(self):
        return len(self.terms)

    def matches(self, rows):
        rows = rows[-len(self.terms):]
        if len(rows) != len(self.terms):
            return None

        for i in range(len(rows)):
            if not self.terms[i].matches(rows[i]):
                return None

        return rows


class Token:
    def __init__(self, line):
        split_line = line.split('=')
        self.name = split_line[0].strip()
        self.tdefs = []
        for tdef in split_line[1].split(','):
            #print(line, tdef)
            tdef = tdef.strip()
            self.tdefs.append(TDef(tdef))

    def matches(self, rows):
        for tdef in self.tdefs:
            subrows = tdef.matches(rows)
            if subrows:
                return subrows
        return None

    def max_size(self):
        return max(len(tdef) for tdef in self.tdefs)


def calc_freqs(data, tokens, stopwords):
    """Create a frequency map out of the new testament

    freqs
        key: lexical form of word
        value: frequency count

    """
    row_queue = []
    row_queue_len = max(token.max_size() for token in tokens)
    all_books = data[0]
    all_books['freqs'] = collections.Counter()
    for i in range(27):
        book = data[i + 1]
        book['freqs'] = collections.Counter()
        for row in pysblgnt.morphgnt_rows(i + 1):
            lex = row['lemma']
            if lex in stopwords:
                continue
            all_books['freqs'][lex] += 1
            book['freqs'][lex] += 1

            # See if we have finished a token
            row_queue.append(row)
            if len(row_queue) > row_queue_len:
                row_queue.pop(0)
            for token in tokens:
                rows = token.matches(row_queue)
                if rows:
                    text = []
                    for match_row in rows:
                        sublex = match_row['lemma']
                        all_books['freqs'][sublex] -= 1
                        book['freqs'][sublex] -= 1
                        text.append(match_row['text'])
                    all_books['freqs'][token.name] += 1
                    book['freqs'][token.name] += 1
                    break


def calc_atfs(data):
    r"""Get augmented term frequencies

    atf = \log{2}{\frac{tf}{max_tf}}

    freqs
        key: lexical form of word
        value: augmented term frequency

    """
    all_atfs = collections.defaultdict(list)
    for book in data[1:]:
        atfs = {}
        freqs = book['freqs']
        # Uncomment the following line for stopword candidates
        #print(freqs.most_common(3))
        _, max_freq = freqs.most_common(1)[0]
        for lex, freq in freqs.items():
            atf = math.log2(1 + freq / max_freq)
            if lex == 'sonofgod':
                print(book['name'], 'sonofgod', freq, max_freq)
            atfs[lex] = atf
            all_atfs[lex].append(atf)
        book['atfs'] = atfs

    # Average atfs over all the books
    avg_atfs = {}
    for lex, atfs in all_atfs.items():
        avg_atfs[lex] = 1 - statistics.mean(all_atfs[lex])
    data[0]['imatfs'] = avg_atfs


def calc_scores(data, terms):
    r"""Get final scores augmented term frequencies

    score = \sum{atf * imatf / N}

    freqs
        key: lexical form of word
        value: score

    """
    all_atfs = collections.defaultdict(list)
    for book in data[1:]:
        score = 0
        for term in terms:
            print(book['name'], term, book['atfs'].get(term, 0),
                  data[0]['imatfs'][term])
            score += book['atfs'].get(term, 0) * data[0]['imatfs'][term]
        score /= len(terms)
        book['score'] = score


def clean_line(line):
    hash_index = line.find('#')
    if hash_index > -1:
        line = line[:hash_index]
    line = line.strip()
    return line


def main():
    """The main routine."""
    # Parse arguments
    parser = argparse.ArgumentParser(description='Quantify motifes in the NT')
    parser.add_argument('--stopwords', dest='stopwords',
                        help='input stopwords.txt')
    parser.add_argument('--tokens', dest='tokens', help='multi-word tokens')
    parser.add_argument('motif_terms', help='input motif.txt')
    args = parser.parse_args()

    # Read the stopwords
    stopwords = []
    if args.stopwords:
        with open(args.stopwords) as f:
            for line in f:
                line = clean_line(line)
                if line:
                    stopwords.append(line)

    # Read the tokens
    tokens = []
    if args.tokens:
        with open(args.tokens) as f:
            for line in f:
                line = clean_line(line)
                if line:
                    tokens.append(Token(line))

    # Read the motif terms
    motif_terms = []
    with open(args.motif_terms) as f:
        for line in f:
            line = clean_line(line)
            if line:
                motif_terms.append(line)

    # This data structure stores all our calculations
    # The first level of keys is the book number, where
    # * 0 represents all books
    # * 1 represents Mat
    # * 27 represents Rev
    # The second level of keys are the various types of data for that book
    # e.g. freqs, maxfreq, etc.
    data = [{
        'name': BOOKS[i],
    } for i in range(28)]
    with Timer('Counting words in the NT'):
        calc_freqs(data, tokens, stopwords)
    for token in tokens:
        if token.name not in data[0]['freqs']:
            print('Token not found:', token.name, file=sys.stderr)
            return 1

    with Timer('Calculating augmented term frequencies'):
        calc_atfs(data)

    with Timer('Calculating final scores '):
        calc_scores(data, motif_terms)
    for book in data[1:]:
        print('{}: {:0.3f}'.format(book['name'], book['score']))

    return 0


if __name__ == '__main__':
    try:
        exit(main())
    except KeyboardInterrupt:
        print('Exiting due to KeyboardInterrupt!', file=sys.stderr)

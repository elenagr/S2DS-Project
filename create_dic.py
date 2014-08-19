__author__ = 'elenagr'

import os
import time
import MySQLdb as mdb
from gensim import corpora
import argparse
import enron
import stemming as stem

from collections import Counter


def customizeDic(freq):

    """
    This function loads an existing dictionary called "dictionary_freq.txt" and reduces its
    vocabulary by ignoring the stopwords and least frequent words (given by the lowest frequency parameter freq)
    :param freq: lowest number of documents where the word was found
    :return: returns the new reduced dictionary
    """

    # Load the stopwords list
    stoplist = enron.getCustomStopwords()

    # Load dictionary
    dic=corpora.Dictionary.load_from_text("dictionary_freq.txt")

    # Create a list with the words that appear in less than N documents given by freq
    once_ids = [tokenid for tokenid, docfreq in dic.dfs.iteritems() if docfreq <= freq]

    # Create a list with the ids of the words in the stopwords list
    stop_ids = [dic.token2id[stopword] for stopword in stoplist
                if stopword in dic.token2id]

    # Eliminate non desired entries in our dictionary
    dic.filter_tokens(once_ids + stop_ids)

    # Assign new ids to the remaining words to adjust for the reduced vocabulary
    dic.compactify()

    # Save the new dictionary for reference
    dic.save_as_text("new_dic.txt")

    return dic

def initializeDic(N):
    """
    This function initialize the dictionary in case there is no any previously saved in disk
    :param N: number of emails to build it (recommended 3)
    :return: returns the dictionary
    """

    print "Initializing dictionary with the first {0} emails \n".format(N)

    # Open the connection to the DB
    connection = mdb.connect('localhost', 'kpmg1', 's2ds', 'enron')
    cur = connection.cursor()

    texts = []
    ids = []

    # Query emails for given ids
    for id in range(1, N):
        cur.execute(" select text from emails where id = {0} ".format(id))
        tmp = cur.fetchall()
        texts.append(tmp[0][0])
        ids.append(id)

    texts_id = zip(ids, texts)

    # Apply stemming to the given text
    texts_stem = stem.stemmingListofStrings(texts_id)
    texts_stem = [text for id, text in texts_stem]

    # Builds a dictionary based on the words found in the given texts
    dictionary = corpora.Dictionary(texts_stem)

    return dictionary


parser = argparse.ArgumentParser(description="Generating a dictionary")
parser.add_argument('-N', '--Ndic', help = 'Number of texts considered for initial dictionary',
                    required = True, type=int)
parser.add_argument('-dic', '--initialize', help='initialize dictionary', default=False, action='store_true')
parser.add_argument('--append', help='append word mapping to existing file', default=False,
                    action='store_true')


def main():
    """
    This function generates a dictionary (map id<-> word) based on the texts saved in the enron database
    In the file dictionary_freq.txt one can see the word id, the word and the number of emails where that
    particular word appear
    There are two dictionary, one in alphabetic order (dictionary_word.txt) and another one ordered by frequency
    (dictionary_freq.txt)
    It also produces a file map_words.txt with the email id and all the words that appear in each of them.
    A complementary file map_freqs.txt contains the frequency for each of the words of the previous file.

    :return:
    """
    # Read arguments:
    args = parser.parse_args()
    N=args.Ndic

    start_code = time.time()

    # Remove files which will be generated within this function to avoid appending to an existing file unless
    # there is an argument which explicitly requires append to existing file
    if (args.append == False):
        if os.path.exists("word_replace_dic.txt"):
            os.remove("word_replace_dic.txt")
        if os.path.exists("ngrams_found.txt"):
            os.remove("ngrams_found.txt")
        if os.path.exists("map_freqs.txt"):
            os.remove("map_freqs.txt")
        if os.path.exists("map_words.txt"):
            os.remove("map_words.txt")

    # Open the connection to the DB
    connection = mdb.connect('localhost', 'kpmg1', 's2ds', 'enron')
    cur = connection.cursor()

    # In our case the IDs are ordered by entry. Otherwise you could do:
    # cur.execute("SELECT COUNT(*) FROM emails;")
    # The last ID number gives us the number of rows of the table.
    cur.execute("select id from emails order by id desc limit 1;")
    res = cur.fetchall()
    size = [int(col) for row in res for col in row]

    # Initialize the dictionary or reads it from file

    if (args.initialize == True):
        dictionary = initializeDic(N)
    else:
        dictionary = corpora.Dictionary.load_from_text("dictionary_words.txt")

    outfrqs = open('map_freqs.txt', 'a+')
    outids = open('map_words.txt', 'a+')

    # Here we go: construct the dictionary and the word-frequency mapping for each email
    for id in range(1, 11):
        cur.execute(" select text from emails where id = {0} ".format(id))
        tmp = cur.fetchall()
        text_stem = stem.stemmingString(tmp[0][0], id)
        # We don't want to count twice the emails already consider in the dictionary. We set the
        # update to false for the emails used to build the dictionary
        if id <= N:
            mytext = dictionary.doc2bow(text_stem, allow_update=False)
        #For the rest we update our dictionary with each new emails
        else:
            mytext = dictionary.doc2bow(text_stem, allow_update=True)

        # Save to file the words and their frequency for each new text
        outids.writelines("{0}; {1}\n".format(id, [idw for idw, frq in mytext]))
        outfrqs.writelines("{0}; {1}\n".format(id, [frq for idw, frq in mytext]))

        # Save dictionary once in a while to make sure we don't loose everything if some error ocurrs
        if id % 1 == 0 or id == (size[0]-1):
            dictionary.save_as_text("dictionary_words.txt", sort_by_word=True)
            dictionary.save_as_text("dictionary_freq.txt", sort_by_word=False)
            print 'Dictionary saved until id = {0}'.format(id)

    end_code = time.time()

    codetime = end_code - start_code

    print 'Total time to create dictionary: {0} sec'.format(codetime)


if __name__ == '__main__':
    main()
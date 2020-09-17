import numpy as np
from nltk import WordNetLemmatizer
from nltk.corpus import wordnet

PATH_STOP_WORDS = 'utils/stop_words_FULL.txt'
PATH_NASARI_SMALL = "./utils/dd-small-nasari-15.txt"
PATH_NASARI = "./utils/dd-nasari.txt"

lemmatizer = WordNetLemmatizer()

#### Read files ####


def load_nasari(path):
    with open(path, 'r') as file:
        lines = file.readlines()
    result, nasari = [], {}

    for line in lines:
        result.append(line.strip().split(';'))

    for row in result:
        b_id = row[0]
        word = row[1].lower()
        synsets = row[2:]
        nasari[word] = []
        tmp = {}

        for syn in synsets:
            syn_splitted = syn.strip().split('_')
            if len(syn_splitted) > 1:
                tmp[syn_splitted[0]] = float(syn_splitted[1])
        nasari[word].append({'b_id': b_id, 'synsets': tmp})
    return nasari


def load_text(path):
    with open(path, 'r') as file:
        lines = file.readlines()
    result = []
    for line in lines:
        if not line.startswith('#') and len(line) > 1:
            result.append(line.strip())
    return result


def build_words_path_set(path):
    res = set()
    with open(path, 'r') as file:
        lines = file.readlines()
    for line in lines:
        res.add(str(line.rstrip()))
    return res

#### Utility ####

def remove_stopwords(words):
    stopwords = build_words_path_set(PATH_STOP_WORDS)
    result = []
    for w in words:
        if w.lower() not in stopwords:
            result.append(w.lower())
    return result


def word_count(text):
    sum = 0
    for paragraph in text:
        sum += len(paragraph.split(' '))
    return sum


def remove_punctuation(string):
    chars = '.,:;!?()”“…-'
    for c in chars:
        string = string.replace(c, '')
    string = string.replace("’s", '')
    return string


def find_most_frequent_words(paragraph):
    res = map(lambda w: w.strip(),
              remove_punctuation(paragraph).lower().split(' '))
    words = remove_stopwords(set(res))
    wsorted = sorted(words)

    freq = []
    for w in wsorted:
        if len(w) > 1:
            c = paragraph.lower().count(w.lower())
            freq.append([w, c])

    return sorted(freq, key=lambda f: f[1], reverse=True)


# get nasari vector of word in frequent_words return a
def get_nasari_vect(frequent_words, nasari):
    result = []
    for w in frequent_words:
        if w[0] in nasari.keys():
            result.append([w[0], nasari[w[0]]])
    return result


#### Ranking method ####


def rank_paragraphs_by_keywords(keywords, paragraphs):
    ranks = []
    for paragraph in paragraphs:
        occurences = 0
        for word in keywords:
            occurences += paragraph.lower().count(word.lower())
        ranks.append(occurences)
    return ranks


def rank_paragraphs_by_cohesion(paragraphs, stopwords):
    # Compares the co-occurences of names in between paragraph
    # retun vect[paragraph] each cell is the rank of paragraph i between the paragraph i + 1
    relevant_terms_for_p = []

    for paragraph in paragraphs:
        words = remove_punctuation(paragraph).split(' ')
        relevant_words = []
        for w in words:
            if len(w) > 1 and w not in stopwords:
                relevant_words.append(lemmatizer.lemmatize(w.lower()))
        relevant_terms_for_p.append(remove_stopwords(relevant_words))

    ranks = [0] * len(paragraphs)
    # i : current paragraph
    # j : next paragraph
    for i in range(len(paragraphs) - 1):
        j = i + 1
        intersection_with_next = set(relevant_terms_for_p[i]).intersection(set(relevant_terms_for_p[j]))
        ranks[i] = len(intersection_with_next)
        ranks[j] += len(intersection_with_next)
    return ranks


def rank_by_weighted_overlap(context, paragraphs, nasari):
    ranks = []
    for paragraph in paragraphs:
        rank = 0
        for w1 in paragraph.split(' '):
            if w1 in nasari:
                for w2 in context:
                    # w1 type string
                    # w2 type list -> ([0]lemma_w2, [1]nasari_vector_of_w2)
                    rank += sim(w1, w2, nasari)
        ranks.append(rank)
    # Compressing value from range [0:50] -> [0:5]
    for i, val in enumerate(ranks):
        ranks[i] = val / 7
    return ranks


def sim(w1, w2, nasari):
    max_sim = 0
    for s1 in wordnet.synsets(w1):
        for s2 in wordnet.synsets(w2[0]):
            ss1 = s1.name().split('.')[0]
            ss2 = s2.name().split('.')[0]
            if ss1 in nasari and ss2 in nasari:
                tmp, o = weighted_overlap(nasari[ss1][0]['synsets'], w2[1][0]['synsets'])
                if tmp > max_sim:
                    max_sim = tmp
    return max_sim


# get rank (len(v1) - index of q in v1)
def rank(q, v1):
    for index, item in enumerate(v1):
        if list(item)[1] == q:
            return index + 1


# Input
# w1 : { w1 : nasari[w1] }
# w2 : { w2 : nasari[w2] }
def weighted_overlap(w1, w2):
    O = set(w1.keys()).intersection(w2.keys())
    # O is the set of the overlap dimension between 2 vector
    rank_acc, den = 0, 0
    if len(O):
        for i, q in enumerate(O):
            den += 1. / (2 * (i + 1))
            # ( rank of q in_w1 + rank of q in_w2 ) ^ (-1)
            rank_acc += 1. / (rank(q, [(v, k) for k, v in w1.items()]) + rank(q, [(v, k) for k, v in w2.items()]))
        return np.sqrt(pow(rank_acc, -1) / den), O
    else:
        return 0.0, O


def summarize_text(text, nasari, compression_rate):
    title, text_summarized = text[0], text[1:]
    num_words = word_count(text[1:])
    stopwords = build_words_path_set(PATH_STOP_WORDS)
    target_num_words = num_words - num_words * compression_rate / 100.

    index = 0
    while num_words > target_num_words:
        print('-' * 20)
        print('Actual paragraphs in text: {}'.format(len(text_summarized)))

        # 1 Find frequence of words in text
        size_frequent_word = 10
        freq_words = find_most_frequent_words(' '.join(text_summarized))[:size_frequent_word]
        print('\n 10 Frequent words: {}'.format(freq_words))

        # 2 Get NASARI vector of most frequent words in text
        context = get_nasari_vect(freq_words, nasari)

        # e Rank paragraph with keyword from title
        keywords = remove_stopwords(title.split(' '))
        key_ranks = np.array(rank_paragraphs_by_keywords(keywords, text_summarized))

        # 4 Rank paragraph with Weighted Overlap
        wo_ranks = np.array(rank_by_weighted_overlap(context, text_summarized, nasari))

        # 5 Rank paragraph with coerenche between parag
        cohesion_ranks = np.array(rank_paragraphs_by_cohesion(text_summarized, stopwords))

        # 6 Sum of all ranks finded
        sum_ranks = wo_ranks + key_ranks
        sum_ranks += cohesion_ranks

        # 7 Remove paragraph with less rank
        print('Paragraph to remove: {}\n'.format(np.argmin(sum_ranks)))
        del text_summarized[np.argmin(sum_ranks)]

        num_words = word_count(text_summarized)
        index += 1

    return [title] + text_summarized


def write_text(text_summeridez, pathfile):
    with open(pathfile, 'w') as file:
        for paragraph in text_summeridez:
            file.write(paragraph)
            file.write('\n\n')


if __name__ == '__main__':
    texts_name = ['Life-indoors.txt', 'Andy-Warhol.txt', 'Ebola-virus-disease.txt', 'Napoleon-wiki.txt']
    n_vectors = load_nasari(PATH_NASARI_SMALL)
    compression_rate = 20

    for text_filename in texts_name:
        print('\n\n********* TEXT NAME {} **********\n'.format(text_filename))
        text_path = 'texts_to_summarize/' + text_filename
        text_summeridez_path = './texts_summarized/' + text_filename

        text = load_text(text_path)

        text_summeridez = summarize_text(text, n_vectors, compression_rate)

        write_text(text_summeridez, text_summeridez_path)

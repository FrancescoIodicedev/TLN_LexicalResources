import numpy as np
import requests
from scipy import stats

KEY_BN = '5664a7b6-a345-4ebf-950f-33e47f587fc2'
PATH_BID_ANN = 'utils/bid_annotated.txt'
PATH_VALSIM_ANN = 'utils/valsim_annotated.tsv'
PATH_NASARI = 'utils/mini_NASARI.tsv'
PATH_SENSE2SYN = 'utils/SemEval17_IT_senses2synsets.txt'


def parse_terms(path):
    with open(path, 'r') as file:
        lines = file.readlines()
    pairs, score = [], []
    for line in lines:
        terms = line.split('\t')
        pairs.append((terms[0].lower().strip(), terms[1].lower().strip()))
        score.append(float(terms[2].strip()))
    return pairs, score


def parse_senses2synsets(path):
    terms = {}
    with open(path, 'r') as file:
        lines = file.readlines()

    curr_term = None
    for line in lines:
        if line.startswith('#'):
            curr_term = line.replace('#', '').strip().lower()
            terms[curr_term] = []
        else:
            terms[curr_term].append(line.strip())
    return terms


def load_nasari_embedded(path):
    with open(path, 'r') as file:
        lines = file.readlines()
    nasari = {}

    for line in lines:
        values = []
        terms = line.split('\t')
        b_id = terms[0].split('__')[0]
        name = terms[0].split('__')[1].replace('_', ' ')
        for n in terms[1:]:
            values.append(float(n))
        vector = np.array(values)
        nasari[b_id] = {'name': name.lower(), 'v': vector}
    return nasari


def cos_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm_a = np.linalg.norm(v1)
    norm_b = np.linalg.norm(v2)
    return dot_product / (norm_a * norm_b)


def calculate_cos_similarity(words, nasari, sense2syn):
    data_cos_similarity = []
    for w1, w2 in words:
        if w1 and w2 in sense2syn:
            sim = get_max_similarity(w1, w2, nasari, sense2syn)
            #normalized cos similarity
            data_cos_similarity.append(sim * 4)
    return data_cos_similarity


def get_max_similarity(w1, w2, nasari, sense2syn):
    max_sim = 0
    for c1 in sense2syn[w1]:
        for c2 in sense2syn[w2]:
            if c1 in nasari and c2 in nasari:
                nasari_vect_w1 = nasari[c1]
                nasari_vect_w2 = nasari[c2]
                sim = cos_similarity(nasari_vect_w1['v'], nasari_vect_w2['v'])
                if sim > max_sim:
                    max_sim = sim
    return max_sim


def arg_max(w1, w2, nasari, sense2syn):
    max_sim, s1, s2 = 0, None, None
    for c1 in sense2syn[w1]:
        for c2 in sense2syn[w2]:
            if c1 in nasari and c2 in nasari:
                nasari_vect_w1 = nasari[c1]
                nasari_vect_w2 = nasari[c2]
                sim = cos_similarity(nasari_vect_w1['v'], nasari_vect_w2['v'])
                if sim > max_sim:
                    max_sim = sim
                    s1 = c1
                    s2 = c2
    return s1, s2


def get_terms_in_synset(synset):
    terms_list = []
    res = requests.get('https://babelnet.io/v5/getSynset?id={}&key={}'.format(synset, KEY_BN))
    response = res.json()
    if 'senses' in response:
        senses_list = response['senses']
        for s in senses_list:
            if s['type'] == 'WordNetSense' or s['type'] == 'BabelSense':
                terms_list.append(s['properties']['fullLemma'])
    #return first 5 terms
    return terms_list[:5]


# Output List(V) -> V = [Term1 Term2 B_ID1 B_ID2 Term_BID1 Term_BID2]
def parse_bn_syns_annotated(path):
    bid_annotated = []
    with open(path, 'r') as file:
        lines = file.readlines()

    for index, line in enumerate(lines):
        l_splitted = line.split('\t')
        if len(l_splitted) != 6:
            print('error line {}'.format(index))
        else:
            bid_annotated.append(l_splitted)
    return bid_annotated


if __name__ == '__main__':
    # decimal digit
    precision_value = 4
    # parse data
    data, manual_score = parse_terms(PATH_VALSIM_ANN)
    nasari = load_nasari_embedded(PATH_NASARI)
    senses2synset = parse_senses2synsets(PATH_SENSE2SYN)
    bnval_annotated = parse_bn_syns_annotated(PATH_BID_ANN)

    # evaluate score of similarity with cosine similary
    result = calculate_cos_similarity(data, nasari, senses2synset)

    # Cosegna 1
    print('-'*50)
    coef, p_value = stats.pearsonr(manual_score, result)
    print('\nCoefficienti di pearson & Spearmain values annotated '
          'manually and values calculate with cosin similairity\n')
    print('Pearson correlation coeffcient : {}'.format(round(coef, precision_value)))
    coef_s, p_value_s = stats.spearmanr(manual_score, result)
    print("Spearman correlation coeffcient : {}\n".format(round(coef_s, precision_value)))
    print('-'*50)
    print('\n\n')

    # Cosegna 2
    correct_match_coplues, correct_match_term = 0, 0
    for i, row in enumerate(bnval_annotated):
        print('**************** Words: w1 = {} w2 = {} ****************\n'.format(row[0], row[1]))
        print('\t Bable synset annotated for w1 : {} with terms {}'.format(row[2], row[4]))
        print('\t Bable synset annotated for w2 : {} with terms {}'.format(row[3], row[5].replace('\n', '')))
        print('\t Head Score: {}'.format(manual_score[i]))
        print('\t Cosin Score: {}'.format(round(result[i], precision_value)))

        s1, s2 = arg_max(row[0].lower(), row[1].lower(), nasari, senses2synset)
        words1 = get_terms_in_synset(s1)
        words2 = get_terms_in_synset(s2)

        print('\t Bable synset calculated for w1 : {} with terms {}'.format(s1, words1))
        print('\t Bable synset calculated for w2 : {} with terms {}\n'.format(s2, words2))

        # Accuracy
        if s1 == row[2] and s2 == row[3]:
            correct_match_coplues = correct_match_coplues + 1
        if s1 == row[2]:
            correct_match_term = correct_match_term + 1
        if s2 == row[3]:
            correct_match_term = correct_match_term + 1

    accuracy_couples = (correct_match_coplues / 60)*100
    accuracy_on_term = (correct_match_term / 120)*100

    print('************** Accuracy ************ \n\t- on couple {} \n\t- on term {}'
          .format(round(accuracy_couples, precision_value), round(accuracy_on_term, precision_value)))
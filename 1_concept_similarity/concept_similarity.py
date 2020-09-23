from math import log
from nltk.corpus import wordnet
from scipy import stats

MAX_DEPTH = 20

##### Utility #####

def read_file(path):
    with open(path, 'r') as file:
        lines = file.readlines()
    lines = lines[1:]
    w1, w2, sim = [], [], []
    for line in lines:
        line_spitted = line.split(',')
        w1.append(line_spitted[0])
        w2.append(line_spitted[1])
        sim.append(float(line_spitted[2]) / 10)
    return w1, w2, sim


##### Support #####


def all_hypernyms(s):
    hypernyms = s.hypernyms() + s.instance_hypernyms()
    for hypernym in hypernyms:
        hypernyms.extend(get_hypernyms(hypernym))
    return hypernyms


def get_hypernyms(s):
    if not s._all_hypernyms:
        s._all_hypernyms = all_hypernyms(s)
    return s._all_hypernyms


def intersection(hp1, hp2):
    return list(set(hp1).intersection(set(hp2)))


def find_LCS(s1, s2):
    hp1 = get_hypernyms(s1)
    hp2 = get_hypernyms(s2)
    common = intersection(hp1, hp2)
    lcs = sorted(common, key=lambda hp: hp.max_depth(), reverse=True)
    if len(lcs) == 0:
        return None
    return lcs[0]


def len_path(s1, s2):
    if s1 == s2:
        return 0
    lcs = find_LCS(s1, s2)
    if lcs:
        d1 = shortest_len_hypernym(s1,lcs)
        d2 = shortest_len_hypernym(s2,lcs)
        return d1 + d2
    return None


def shortest_len_hypernym(sense, hypernym):
    hypernyms_distance = [(sense, 0)]
    paths = {}

    while len(hypernyms_distance) > 0:
        sense_depth = hypernyms_distance[0]
        sense, depth = sense_depth[0], sense_depth[1]
        del hypernyms_distance[0]

        if sense in paths:
            continue

        paths[sense] = depth
        depth += 1
        hypernyms_distance.extend([(hyp, depth) for hyp in sense._hypernyms()])
        hypernyms_distance.extend([(hyp, depth) for hyp in sense._instance_hypernyms()])

    return paths[hypernym]


def max_depth_of_tree():
    return max(max(len(path) for path in sense.hypernym_paths()) for sense in wordnet.all_synsets())


def min_depth(synset):
    highest_senses, distances = synset.root_hypernyms(), []

    for sense in highest_senses:
        distances.append(shortest_len_hypernym(synset, sense))

    return min(distances)


##### Metrics #####

def shortest_path(w1, w2):
    min_length = MAX_DEPTH * 2
    for s1 in wordnet.synsets(w1):
        for s2 in wordnet.synsets(w2):
            len = len_path(s1,s2)
            if len:
                if len < min_length:
                    min_length = len
    return 2 * MAX_DEPTH - min_length


def wu_palmer_similarity(w1, w2):
    max_sim = 0
    for s1 in wordnet.synsets(w1):
        for s2 in wordnet.synsets(w2):
            lcs = find_LCS(s1, s2)
            if lcs:
                sim = 2 * min_depth(lcs) / (min_depth(s1) + min_depth(s2))
                if sim > max_sim:
                    max_sim = sim
    return max_sim


def leakcock_chodorow_similarity(w1, w2):
    max_sim = 0
    for s1 in wordnet.synsets(w1):
        for s2 in wordnet.synsets(w2):
            len = len_path(s1,s2)
            if len:
                if len > 0:
                    sim = -(log(len / (2 * MAX_DEPTH)))
                else:
                    sim = -(log(len + 1 / (2 * MAX_DEPTH + 1)))
            else:
                sim = 0
            if sim > max_sim:
                max_sim = sim
    return max_sim


if __name__ == '__main__':
    wu, sp, lc = [], [], []
    w1, w2, target = read_file("utils/WordSim353.csv")

    for i in range(len(w1)):
        wu.append(wu_palmer_similarity(w1[i], w2[i]))
        sp.append(shortest_path(w1[i], w2[i]))
        lc.append(leakcock_chodorow_similarity(w1[i], w2[i]))

    print("\n---------Pearson correlation for:---------\n")
    r, prob = stats.pearsonr(wu, target)
    print('Wu & Palmer metric\n\t- Value : {}\n'.format(round(r,4)))
    r, prob = stats.pearsonr(sp, target)
    print('Shortest path metric\n\t-  Value : {}\n'.format(round(r,4)))
    r, prob = stats.pearsonr(lc, target)
    print("Leakcock & Chodorow metric\n\t- Value : {}\n".format(round(r,4)))

    print("\n---------Spearman correlation for:---------\n")
    r, prob = stats.spearmanr(wu, target)
    print('Wu & Palmer metric\n\t- Value : {}\n'.format(round(r,4)))
    r, prob = stats.spearmanr(sp, target)
    print('Shortest path metric\n\t-  Value : {}\n'.format(round(r,4)))
    r, prob = stats.spearmanr(lc, target)
    print("Leakcock & Chodorow metric\n\t- Value : {}\n".format(round(r,4)))
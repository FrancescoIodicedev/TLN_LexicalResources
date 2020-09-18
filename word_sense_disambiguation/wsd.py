from nltk.corpus import wordnet as wn
from nltk.stem import WordNetLemmatizer
from nltk.corpus.reader.wordnet import Lemma
from nltk.corpus import semcor
from nltk.wsd import lesk
from sklearn.metrics import accuracy_score
import re

stop_words_set = set()
lemmatizer = WordNetLemmatizer()


##### Utility #####

def read_sentences(path):
    sentences, target_value = {}, []
    file = open(path, 'r')
    for line in file.readlines():
        sentences_target = line.split('|')
        target =''
        for w in sentences_target[0].split(' '):
            if w.startswith('*'):
                target = w.replace('*', '')
                break
        sentences[sentences_target[0].replace('*', '').strip()] = remove_punctuation(target)
        target_value.append(sentences_target[1].replace('\n', ''))
    file.close()
    return sentences, target_value


def build_words_path_set(path):
    res = set()
    with open(path, 'r') as file:
        lines = file.readlines()
    for line in lines:
        res.add(str(line.strip()))
    return res


def remove_punctuation(string):
    punctuation = '?()”“…-.,:;!'
    for char in punctuation:
        string = string.replace(char, '')
    string = string.replace("’s", '')
    string = string.replace("\n", '')
    return string


def intersection(first_set, second_set):
    intersection_set = set()
    for var in first_set:
        if var in second_set:
            intersection_set.add(var)
    return intersection_set


def union(s1, s2):
    res = set()
    for var in s1:
        res.add(var)
    for var in s2:
        if var not in res:
            res.add(var)
    return res


##### Support #####

def filter_stopword_from_sentence(sentence):
    relevant_words = set()
    for s in sentence.split(' '):
        if s not in stop_words_set:
            relevant_words.add(remove_punctuation(s))
    return relevant_words


def get_words_from_examples(examples):
    words = set()
    if len(examples) > 0:
        for example in examples:
            for word in example.split():
                words.add(remove_punctuation(word))
    return words


def get_words_from_definition(param):
    words = set()
    for word in param.split(' '):
        if words not in stop_words_set:
            words.add(word)
    return words


def get_wordnet_ctx(sense):
    res = set()
    words_examples = get_words_from_examples(sense.examples())
    words_definition = get_words_from_definition(sense.definition())
    contex = union(words_examples, words_definition)

    # Hyponym contex
    for hyponym in sense.hyponyms():
        hyponym_ctx_word = union(get_words_from_examples(hyponym.examples()),
                                 get_words_from_definition(hyponym.definition()))
        contex = union(hyponym_ctx_word, contex)

    # Hypernym contex
    for hypernym in sense.hypernyms():
        hypernym_ctx_word = union(get_words_from_examples(hypernym.examples()),
                                  get_words_from_definition(hypernym.definition()))
        contex = union(hypernym_ctx_word, contex)

    # Filter stopword
    for w in contex:
        if w not in stop_words_set:
            res.add(lemmatizer.lemmatize(w))

    return res


def get_semcor_sentences(data_size):
    sentences, senses = [], []
    for index in range(0, data_size):
        for node in semcor.tagged_sents(tag='both')[index]:
            node_noun = None
            # If node is a noun
            if isinstance(node.label(), Lemma) and node[0].label() == 'NN':
                node_noun = node
                break
        if node_noun:
            senses.append(node)
            sentences.append(" ".join(semcor.sents()[index]))
    return sentences, senses


##### Lesk #####


def lesk_algorithm(word, sentence):
    senses = wn.synsets(word)
    if len(senses) == 0:
        return None
    else:
        best_sense = wn.synsets(word)[0]
        max_overlap = set()
        context = filter_stopword_from_sentence(sentence)
        for sense in wn.synsets(word):
            signature = get_wordnet_ctx(sense)
            overlap = intersection(signature, context)
            if len(overlap) > len(max_overlap):
                max_overlap = overlap
                best_sense = sense
        return best_sense


if __name__ == '__main__':
    # Consegna 1
    print('*'*50)
    sentences, sense_target = read_sentences('utils/sentences.txt')
    for i, s in enumerate(sentences.keys()):
        sense = lesk_algorithm(lemmatizer.lemmatize(sentences[s].lower()), s)
        print('\nSentence : {}\nWord Target : {}\nSense inferred {}\nSense Target {}'.format(s, sentences[s], sense, sense_target[i]))
        if str(sense) == sense_target[i]:
            print("Result: OK")
        else:
            print("Result: FAIL")
        new_sentence = s.replace(sentences[s], '[' + ' '.join([str(elem) for elem in sense.lemma_names()]) + ']')
        print('Sentence with synonym : {}\n'.format(new_sentence))
    # Consegna 2
    print('*'*50)

    data_size = 50
    stop_words_set = build_words_path_set('utils/stop_words_FULL.txt')
    sentences, nouns = get_semcor_sentences(data_size)
    target = [str(w.label().synset()) for w in nouns]
    result, result_nltk = [], []

    for i in range(len(nouns)):
        word = re.sub(r'[^\w\s]', '', nouns[i][0][0])
        lesk_res = lesk_algorithm(word, sentences[i])
        lesk_res_nltk = lesk(sentences[i], word)
        result.append(str(lesk_res))
        result_nltk.append(str(lesk_res_nltk))

    for i in range(len(sentences)):
        print("\nTarget: ", target[i])
        print("Inferred: ", result[i])
        if target[i] == result[i]:
            print("Result: OK")
        else:
            print("Result: FAIL")
    print("\n")

    print("WSD accuracy with Hyponym and Hypernym terms: {:.0f}%\n".format(accuracy_score(target, result) * 100))
    print("WSD of nltk : {:.0f}%".format(accuracy_score(target, result_nltk) * 100))

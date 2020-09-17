import hashlib
import spacy
from nltk.corpus import framenet as fn
from random import randint
from random import seed
from word_sense_disambiguation.wsd import lesk_algorithm

NOT_FOUND = 'NOT_FOUND'
FRAME_NAME = 0
FRAME_ELEMENT = 1
LEXICAL_UNIT = 2

#  the data structure used to represent the annotation of the various
#  terms in the frames is a list of this element:
#
#  element structure
#   [ { frame_name, synset} ,
#       [ {frame_element, synset} .. }],
#       [ {lexical_unit, synset} .. }]
#


def print_frames_with_IDs():
    for x in fn.frames():
        print('{}\t{}'.format(x.ID, x.name))


def get_frams_IDs():
    return [f.ID for f in fn.frames()]


def print_frame(id):
    f = fn.frame_by_id(id)
    print('NAME: {}[{}]\tDEF: {}'.format(f.name, f.ID, f.definition))

    print('\n____ FEs ____')
    FEs = f.FE.keys()
    for fe in FEs:
        fed = f.FE[fe]
        print('\tFE: {}\tDEF: {}'.format(fe, fed.definition))
        print(fed.definition)

    print('\n____ LUs ____')
    LUs = f.lexUnit.keys()
    for lu in LUs:
        print(lu)


def getFrameSetForStudent(surname, list_len=5):
    id_framelist = []
    nof_frames = len(fn.frames())
    base_idx = (abs(int(hashlib.sha512(surname.encode('utf-8')).hexdigest(), 16)) % nof_frames)
    print('\nstudent: ' + surname)
    framenet_IDs = get_frams_IDs()
    i = 0
    offset = 0
    seed(1)
    while i < list_len:
        fID = framenet_IDs[(base_idx + offset) % nof_frames]
        f = fn.frame(fID)
        fNAME = f.name
        print('\tID: {a:4d}\tframe: {framename}'.format(a=fID, framename=fNAME))
        offset = randint(0, nof_frames)
        i += 1
        id_framelist.append(fID)
    return id_framelist


##### Utility #####


def find_reggent_of_expression(name):
    nlp = spacy.load('en')
    string = name.replace('_', ' ')
    reggent = string
    if string.count(' ') != 0:
        doc = nlp(string)
        for token in doc:
            if token.dep_ == 'ROOT':
                reggent = token.string
    return reggent.replace(' ', '')


# read manual annotation
def parsing_data_target(path):
    with open(path, 'r') as file:
        lines = file.readlines()
    list_of_frames, index = [], 0

    while index < len(lines):
        frame_name, frame_elements, lexical_units = {}, {}, {}
        result = lines[index].split(':')
        frame_name[result[0].strip()] = result[1].strip().replace('\n', '')
        index += 2

        while lines[index] != '\n':
            result = lines[index].split(':')
            frame_elements[result[0].strip()] = result[1].strip().replace('\n', '')
            index += 1
        index += 1

        while index < len(lines) and lines[index] != '\n':
            result = lines[index].split(':')
            lexical_units[result[0].strip()] = result[1].strip().replace('\n', '')
            index += 1
        list_of_frames.append([frame_name, frame_elements, lexical_units])
        index += 2

    return list_of_frames


def get_accuracy(obtained,target):
    correct_match, total_data, index_obtained, index, index_obtained_elem = 0, 0, 0, 0, 0
    for elem in target:
        print('\nFrame Name : {}\n'.format(elem[0].keys()))
        while index < len(elem):
            for value in elem[index].keys():
                total_data += 1
                print('For the element: |{}| :\n\tsense result : |{}|\n\tsense target: |{}| '
                      .format(value, obtained[index_obtained][index].get(value), elem[index][value]))
                if elem[index][value] == obtained[index_obtained][index].get(value):
                    correct_match += 1
                    print("Result: ", "OK")
                else:
                    print("FAIL")
                print('\n')
            index += 1
        print('*'*100)
        index_obtained += 1
        index = 0
    return total_data, correct_match


def build_fn_data(frame_id):
    frame_name, frame_elements, lexical_units = {}, {}, {}
    f = fn.frame_by_id(frame_id)

    frame_name[f.name] = ''

    for fe in f.FE.keys():
        frame_elements[fe] = ''

    for lu in f.lexUnit.keys():
        lexical_units[lu] = ''

    return [frame_name, frame_elements, lexical_units]


def is_normalidez(sentece):
    if '_' in sentece or '.' in sentece:
        return False
    else:
        return True


def normalizes_string(sentence):
    parzial_val = sentence
    if '.' in sentence:
        parzial_val = sentence.split('.')[0]
    if '_' or ' ' in parzial_val:
        # search on wordnet
        return find_reggent_of_expression(parzial_val)
    return parzial_val

#### Mapping algorithm ####


def map_terms_to_senses(frames):
    # for each frame
    for frame in frames:
        f = fn.frame(list(frame[0].keys())[0])
        # for each section in a single frame
        for index in range(len(frame)):
            # for a term in a single section
            for value in frame[index].keys():
                # if contains . or pos tag
                w = value
                if not is_normalidez(value):
                    w = normalizes_string(value)

                # FRAME NAME
                if index == FRAME_NAME:
                    # Ctx(w) f.definition
                    best_sense = lesk_algorithm(w, f.definition)
                    frame[index][value] = str(best_sense).strip()

                # FRAME ELEMENT
                if index == FRAME_ELEMENT:
                    # Ctx(w) = f.FE[value].definition
                    best_sense = lesk_algorithm(w, f.FE[value].definition)
                    frame[index][value] = str(best_sense).strip()

                # LEXICAL UNIT
                if index == LEXICAL_UNIT:
                    # Ctx(w) = f.lexUnit[value].definition
                    best_sense = lesk_algorithm(w, f.lexUnit[value].definition)
                    frame[index][value] = str(best_sense).strip()

    return frames


if __name__ == '__main__':
    target = parsing_data_target("./utils/framenet_data.txt")

    framelist = getFrameSetForStudent('Iodice')

    print('*'*100)
    print('\n')
    frames = []
    for id in framelist:
        frames.append(build_fn_data(id))

    obtained = map_terms_to_senses(frames)

    total, correct = get_accuracy(obtained, target)
    print('\nTotal {} terms, the correct match are {}, with Accuracy: {}%'
          .format(total, correct, round(correct*100/total), 2))

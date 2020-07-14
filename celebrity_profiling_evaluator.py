#!/usr/bin/python3
import argparse
import sys
import json
from collections import Counter
from statistics import mean
import re
# from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

EV_OUT = r"C:\Users\ALPI\PycharmProjects\Celebrity-Profiling\evaluation.prototext"


def iterload(file):
    buffer = ""
    dec = json.JSONDecoder()
    for line in file:
        buffer = buffer.strip(" \n\r\t") + line.strip(" \n\r\t")
        while(True):
            try:
                r = dec.raw_decode(buffer)
            except:
                break
            yield r[0]
            buffer = buffer[r[1]:].strip(" \n\r\t")


def clean_text(text):
    """
    Applies some pre-processing on the given text.

    Steps :
    - Removing HTML tags
    - Removing punctuation
    - Lowering text
    """

    # remove HTML tags
    text = re.sub(r'<.*?>', '', text)

    # remove the characters [\], ['] and ["]
    text = re.sub(r"\\", "", text)
    text = re.sub(r"\'", "", text)
    text = re.sub(r"\"", "", text)

    # convert text to lowercase
    text = text.strip().lower()

    # replace punctuation characters with spaces
    filters='!"\'#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n'
    translate_dict = dict((c, " ") for c in filters)
    translate_map = str.maketrans(translate_dict)
    text = text.translate(translate_map)

    return text


def parse_input():
    """
    read the files given as parameters and load the newline-delimited json stings
    :return: a tuple with   [0] a list of dicts with predicted classes,
                            [1] a list of dicts with the true classes.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--predictions", help="path to the dir holding the predicted labels.ndjson")
    parser.add_argument("-t", "--truth", help="path to the dir holding the true labels.ndjson")
    parser.add_argument("-o", "--output", help="path to the dir to write the results to")
    args = parser.parse_args()

    # dont presume all are in the same order:
    pred = {json.loads(u)["id"]: json.loads(u)
            for u in open(r"C:\Users\ALPI\PycharmProjects\Celebrity-Profiling\labels.ndjson".format(args.predictions)).readlines()}
    tr = {json.loads(u)["id"]: json.loads(u)
            for u in open(r"C:\Users\ALPI\PycharmProjects\Celebrity-Profiling\labels.ndjson".format(args.truth)).readlines()}
    ids = pred.keys()

    return ([pred[i] for i in ids],
            [tr[i] for i in ids],
            args.output)


def write_output(filename, k, v):
    """
    print() and write a given measurement to the indicated output file
    :param filename: full path of the file, where to write to
    :param k: the name of the metric
    :param v: the value of the metric
    :return: None
    """
    line = 'measure{{\n  key: "{}"\n  value: "{}"\n}}\n'.format(k, str(v))
    print(line)
    open(EV_OUT, "a").write(line)


def harmonic_mean(l):
    """
    calculate the harmonic mean of a list of classes
    :param l: a list holding elements
    :return:
    """
    return len(l) / sum([1 / x for x in l])


def mc_prec_rec(mc_p, mc_t, hit_function=lambda x, y: x == y):
    """
    computes multi value recall and precision. Indices of inputs must match.
    :param hit_function: function to calculate true positives
    :param mc_p: list of predicted values
    :param mc_t: list of true values.
    :return: tuple: list of precision for classes, list of recall for class
    """

    def safe_divide(x, y):
        """ basically defines the precision as 0 if nothing is predicted as true"""
        return x / y if y != 0 else 0

    true_positive = [t for p, t in zip(mc_p, mc_t) if hit_function(p, t)]
    false_positives = [p for p, t in zip(mc_p, mc_t) if not hit_function(p, t)]
    positive_in_prediction = true_positive + false_positives
    positive_in_truth = Counter(mc_t)

    tp_c = Counter(true_positive)
    pp_c = Counter(positive_in_prediction)

    precisions = [safe_divide(tp_c.get(cls, 0), pp_c.get(cls, 0))
                  for cls in positive_in_truth.keys()]
    recalls = [tp_c.get(cls, 0) / positive_in_truth.get(cls, 0) for cls in positive_in_truth.keys()]

    return precisions, recalls


def age_window_hit(by_predicted, by_truth, m=lambda x: -0.1 * x + 202.8):
    """
    calculates the window for a given truth and checks if the prediction lies within that window
    :param by_predicted: the predicted birth year
    :param by_truth: the true birth year
    :param m: function giving the window size when given by_truth.
    :return: true if by_predicted within m-window of by_truth
    """
    return int(by_truth - m(by_truth)) <= by_predicted <= int(by_truth + m(by_truth))


if __name__ == "__main__":
    """
    This is the evaluator for the PAN@CLEF19 Task "Celebrity Profiling"
    It outputs 5 Metrics: 
      - cRank, the harmonic mean of the sub metrics below. This is the primary metric. 
      - F1_gender, the harmonic mean of the average multi class precision and recall for gender prediction
      - F1_occupation, same as above for occupation
      - F1_fame, same as above for fame
      - F1_age, same as above, but positives are calculated leniently in a window around the prediction
      
    For more information visit: 
      - https://pan.webis.de/clef19/pan19-web/celebrity-profiling.html
      
    Please send any requests or remarks to:
      - matti.wiegmann@uni-weimar.de
      - pan@webis.de
    """
    predictions, truth, output_dir = parse_input()

    # https://medium.com/@bedigunjit/simple-guide-to-text-classification-nlp-using-svm-and-naive-bayes-with-python-421db3a72d34
    # https://medium.com/data-from-the-trenches/text-classification-the-first-step-toward-nlp-mastery-f5f95d525d73

    # this vectorizer will skip stop words
    # vectorizer = CountVectorizer(stop_words="english", preprocessor=clean_text)
    # fit the vectorizer on the training text
    # vectorizer.fit(training_texts)
    # # get the vectorizer's vocabulary
    # inv_vocab = {v: k for k, v in vectorizer.vocabulary_.items()}
    # vocabulary = [inv_vocab[i] for i in range(len(inv_vocab))]
    #
    # # vectorization example
    # pd.DataFrame(
    #     data=vectorizer.transform(test_texts).toarray(),
    #     index=["test sentence"],
    #     columns=vocabulary
    # )

    gender_prec, gender_rec = mc_prec_rec([u["gender"] for u in predictions],
                                          [u["gender"] for u in truth])
    occ_prec, occ_rec = mc_prec_rec([u["occupation"] for u in predictions],
                                    [u["occupation"] for u in truth])
    fame_prec, fame_rec = mc_prec_rec([u["fame"] for u in predictions],
                                      [u["fame"] for u in truth])
    age_prec, age_rec = mc_prec_rec([u["birthyear"] for u in predictions],
                                    [u["birthyear"] for u in truth], hit_function=age_window_hit)

    f1_gender = harmonic_mean([mean(gender_prec), mean(gender_rec)])
    f1_occupation = harmonic_mean([mean(occ_prec), mean(occ_rec)])
    f1_fame = harmonic_mean([mean(fame_prec), mean(fame_rec)])
    f1_age = harmonic_mean([mean(age_prec), mean(age_rec)])

    for k, v in {"c_rank": harmonic_mean([f1_gender, f1_occupation, f1_fame, f1_age]),
                 "f1_gender": f1_gender, "f1_occupation": f1_occupation,
                 "f1_fame": f1_fame, "f1_age": f1_age}.items():
        write_output("{}/{}".format(output_dir, EV_OUT), k, v)


    # read line by line
    with open(r"C:\Users\ALPI\PycharmProjects\Celebrity-Profiling\feeds.ndjson", encoding="utf8") as f:
        # distros_dict = json.load(f)
        count = 0
        for o in iterload(f):
            print("COUNT : ", count)
            print("Working on an ", "id: ", o['id'], " text: ", o['text'])
            count += 1
            if count == 100:
                break
    # for distro in distros_dict:
    #     print(distro['id'])

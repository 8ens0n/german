#!/usr/bin/env python3

from bs4 import BeautifulSoup
import requests
import hashlib
import yaml
import argparse
from pathlib import Path
from unicodedata import normalize

DICT_PATH = ".dict"
DICT_ONLINE_URL = "https://www.linguee.com/english-german/search"


class Dict:
    def __init__(self):
        # look for an existing .dict file. If it doesn't exist it's ok
        if not Path(DICT_PATH).exists():
            self.known_words = {}
        else:
            with open('.dict', 'r') as vocab:
                my_words = yaml.load(vocab.read(), Loader=yaml.FullLoader)
                self.known_words = {} if my_words is None else my_words

    def query_linguee(self, word):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

        result = requests.get(DICT_ONLINE_URL, headers=headers, params={"source": "auto", "query": word})
        if result.status_code == 200:
            return result.content.decode("ISO-8859-15")
        else:
            return None

    def translate(self, word, filter_type=None):
        output = {}
        linguee_resp = self.query_linguee(normalize('NFC', word))
        if linguee_resp is None:
            return output  # Linguee responded a non 200 response

        soup = BeautifulSoup(linguee_resp, "html.parser")

        de_groups = soup.find_all("div", class_="isForeignTerm", attrs={"data-source-lang": "DE"})

        if len(de_groups) == 0:
            return output  # Linguee doesn't know this word

        groups = de_groups[0].find_all("div", class_="lemma featured")

        for group in groups:
            linguee_word = group.find("a", class_="dictLink").text if group.find("a", class_="dictLink") else None
            linguee_type = group.find("span", class_="tag_wordtype").text if group.find("span", class_="tag_wordtype") else None

            if linguee_word is None or linguee_type is None:
                print("Linguee could not find a word or type for {}".format(word))
                continue

            if "proper" in linguee_type:  # I don't care about proper noun translation
                continue
            elif "neuter" in linguee_type:
                type = "das"
            elif "plural" in linguee_type or "feminine" in linguee_type:
                type = "die"
            elif "masculine" in linguee_type:
                type = "der"
            elif "adverb" in linguee_type:
                type = "adv"
            elif "verb" in linguee_type:
                type = "verb"
            elif "adjective" in linguee_type:
                type = "adj"
            elif "preposition" in linguee_type:
                type = "prep"
            elif "conjunction" in linguee_type:
                type = "conj"
            else:
                continue

            if filter_type and type != filter_type:
                continue

            translation = []
            eg_de = []
            eg_en = []
            for line in group.find_all("div", class_="translation sortablemg featured"):
                translation.append(line.find("a", class_="dictLink featured").text)
                for example in line.find_all("div", class_="example line"):
                    eg_de.append(example.find("span", class_="tag_s").text)
                    eg_en.append(example.find("span", class_="tag_t").text)

            output[hashword(linguee_word+';'+type)] = {
                "type": type,
                "word": linguee_word,
                "translation": translation,
                "eg_de": eg_de,
                "eg_en": eg_en
            }
        return output

    def add_to_dict(self, word, tags, filter_type):
        translated_word = self.translate(word, filter_type)
        if translated_word:
            with open(DICT_PATH, 'a') as file:
                for key in translated_word:
                    if key in self.known_words:
                        print("{} [{}] is already in your dictionary. Skipping".format(translated_word[key]["word"],
                                                                                       translated_word[key]["type"]))
                        continue
                    else:
                        translated_word[key]['tag'] = tags
                        file.write(yaml.dump({key: translated_word[key]}, allow_unicode=True, sort_keys=False))
                        print("Added {} [{}]:  {} to the dictionary".format(translated_word[key]["word"],
                                                                            translated_word[key]["type"],
                                                                            translated_word[key]["translation"]))
        else:
            print("Could find a translation for {} in linguee".format(word))


def hashword(word_to_hash):
    return hashlib.md5(word_to_hash.encode()).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Add new german word to your dictionary')
    parser.add_argument('--words', help='The word you want to add', nargs='+', default=[])
    parser.add_argument('--tags', help="tag the words", required=False, nargs='+', default=[])
    parser.add_argument('--type', help="filter. Only add the specific type der,die,das,...",
                        choices=['der', 'die', 'das', 'adv', 'adj', 'conj', 'prep', 'verb'])
    options = parser.parse_args()
    translator = Dict()
    print("tags: {}".format(options.tags))
    for word in options.words:
        translator.add_to_dict(word, options.tags, options.type)

#!/usr/bin/env python3
import vlc
from util.utils import stderr_redirector
import _thread
from pyfiglet import Figlet
from time import sleep
import argparse
from clint.textui import colored, puts, indent, prompt
import yaml
from os import devnull
from random import randint
from unicodedata import normalize
import re
from datetime import date, datetime

URL_READER = "https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={}&tl=de"


class Quiz:
    def __init__(self, mute=False, tag=None, missed=False):
        dictionary = yaml.load(open(".dict").read(), Loader=yaml.FullLoader)
        if not tag:
            self.vocab = [dictionary[key] for key in dictionary]
        else:  # Filter by tag
            self.vocab = [dictionary[key] for key in dictionary if tag in dictionary[key]['tag']]

        if missed:
            recent_missed_words = self.get_missed()
            self.vocab = [skip for skip in self.vocab if "'{}'".format(skip["word"]) in recent_missed_words]
        self.print_title(mute)

    def get_missed(self):
        missed = []
        today = datetime.now().strftime("%Y-%m-%d")
        with open(".stat") as file:
            lines = file.readlines()
            for line in lines:
                if today not in line:
                    continue
                words = re.search(r"missed \[(.*)\]", line).group(1)
                if words:
                    for word in words.split(","):
                        missed.append(word.strip())
        return missed

    def print_title(self, mute=False):
        p = vlc.MediaPlayer('util/sounds/german.m4a')
        if not mute:
            p.play()
        f = Figlet(font='banner3-D')
        sleep(2.6 if not mute else 0)
        print(f.renderText(' German '))
        sleep(2.9 if not mute else 0)
        print(f.renderText('    Quiz !!!'))
        sleep(2.9 if not mute else 0)
        print(".................................................... (not) by John Cena")
        sleep(2.6 if not mute else 0)
        puts(colored.green('Translate the following words ({} words filtered)'.format(len(self.vocab))))
        sleep(5)

    def play(self, guess):
        try:
            if guess['type'] not in ["der", "die", "das"]:
                words_to_read = guess['word']
            else:
                # pronounce the article if the dictionary entry to read is a noun
                # help me remember the article when I hear with the words
                words_to_read = "{}+{}".format(guess['type'], guess['word'])

            url = URL_READER.format(words_to_read)
            p = vlc.MediaPlayer(url)

            with stderr_redirector(open(devnull, 'w')):
                _thread.start_new_thread(p.play())
        except:
            pass

    def ask(self, revert=False):
        """
        returns:
        -1 when there are no more words in the dictionnary
        0 when the guess is wrong
        1 when the guess is right
        :param revert:
        :return:
        """
        missed = None

        if len(self.vocab) == 0:
            return -1, missed

        index = randint(0, len(self.vocab)-1)
        guess = self.vocab.pop(index)
        rc = 0

        with indent(4, quote=' >'):
            context = '' if 'context' not in guess or not guess['context'] else "(context: {})".format(guess['context'])
            if not revert:
                puts(colored.cyan('{} ({}) {}'.format(guess['word'], guess['type'], context)))
                self.play(guess)
            else:
                type = 'noun' if re.match(r"der|die|das", guess['type']) else guess['type']
                puts(colored.cyan('{} ({}) {}'.format(guess['translation'], type, context)))

        answer = prompt.query('  ')
        while revert and guess["type"] in ["der", "die", "das"] and not re.match(r"(der|die|das) (\w+)", answer):
            puts('start with article for nouns: ')
            answer = prompt.query(' ')

        with indent(4, quote=' >>'):
            if not revert:
                if answer not in guess['translation']:
                    puts(colored.red('wrong guess: {}'.format(guess['translation'])))
                    missed = guess['word']
                else:
                    puts(colored.green('nice: {}'.format(guess['translation'])))
                    rc = 1
            else:
                self.play(guess)
                guess_word = guess['word'] if guess['type'] not in ["der", "die", "das"] else '{} {}'.format(guess['type'],
                                                                                                             guess['word'])
                if normalize('NFC', answer) != normalize('NFC', guess_word):
                    puts(colored.red('wrong guess: {} ({})'.format(guess['word'], guess['type'])))
                    missed = guess['word']
                else:
                    puts(colored.green('nice: {} ({})'.format(guess['word'], guess['type'])))
                    rc = 1

            if 'extra' in guess and guess['extra']:
                puts(colored.yellow(guess['extra']))

            # show example usage when available
            if guess['eg_de']:
                example_index = randint(0, len(guess['eg_de']) - 1)
                puts('{} | {}'.format(guess['eg_de'][example_index], guess['eg_en'][example_index]))
            return rc, missed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test your German vocabulary.')
    parser.add_argument('number', help='number of guess rounds', type=int)
    parser.add_argument('--mute', help='mute sound effect', action='store_true', required=False)
    parser.add_argument('--revert', help='shows translation asks for word', action='store_true', required=False)
    parser.add_argument('--tag', help="a tag to filter the words", required=False)
    parser.add_argument('--missed', help="repeat only missed words of the day", required=False, action="store_true")
    options = parser.parse_args()

    quiz = Quiz(mute=options.mute, tag=options.tag, missed=options.missed)
    round_number = options.number
    good_answer_count = 0

    iteration = 0
    return_code = 0
    missed = []

    start_time = datetime.now()
    while iteration < round_number and return_code != -1:
        return_code, wrong_word = quiz.ask(options.revert)

        if return_code != -1:  # A question was asked and answered
            if wrong_word:
                missed.append(wrong_word)
            iteration += 1
            if return_code == 1:
                good_answer_count += 1
        sleep(2)
        puts('')
    end_time = datetime.now()

    success_rate = round(good_answer_count * 100 / iteration)
    pratice_length = divmod((end_time - start_time).total_seconds(), 60)

    stat = 'date [{date_time}], duration [{min}m {sec}sec], tag [{tag}], success_rate [{rate}%],' \
           ' sample [{iteration} words], revert [{revert}], missed {missed}'.format(date_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
                                                                  min=int(pratice_length[0]),
                                                                  sec=int(pratice_length[1]),
                                                                  tag=options.tag,
                                                                  rate=success_rate,
                                                                  iteration=iteration,
                                                                  revert=options.revert,
                                                                  missed=missed)
    puts(colored.yellow(stat))
    with open('.stat', 'a') as mystat:
        mystat.write('\n{}'.format(stat))

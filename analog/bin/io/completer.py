from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import Completion, Completer
import re
from itertools import chain


class AnalogCompleter(Completer):

    def __init__(self, words, ignore_case=False, meta_dict=None, WORD=False,
                 sentence=False, match_middle=False):
        assert not (WORD and sentence)

        self.words = words
        self.ignore_case = ignore_case
        self.meta_dict = meta_dict or {}
        self.WORD = WORD
        self.sentence = sentence
        self.match_middle = match_middle


    def get_completions(self, document, complete_event):
        words = self.words
        text_before_cursor = document.text_before_cursor
        word_before_cursor = document.get_word_before_cursor(WORD=self.WORD)
        if self.ignore_case:
            word_before_cursor = word_before_cursor.lower()


        def word_matches(word):
            """ True when the word before the cursor matches. """
            if self.ignore_case:
                word = word.lower()

            if self.match_middle:
                return word_before_cursor in word
            else:
                return word.startswith(word_before_cursor)


        def text_matches(cmd: list):
            for c in cmd:
                if self.ignore_case:
                    c = c.lower()
                if text_before_cursor[document.find_previous_word_beginning(WORD=True):].lower().startswith(c):
                    return True
            return False


        def is_first_command():
            if not text_before_cursor:
                return True
            if re.match("^\s*[\S]*$", text_before_cursor):
                return True
            return False


        if is_first_command():
            for w in words[0]:
                if word_matches(w):
                    yield Completion(w, -len(word_before_cursor))

        elif word_before_cursor != "":
            for a in chain(*(w for w in words)):
                if word_matches(a):
                    display_meta = self.meta_dict.get(a, '')
                    yield Completion(a, -len(word_before_cursor), display_meta=display_meta)
        elif text_matches(["set"]):
            for i in ["time", "hour", "day", "month", "year"]:
                yield Completion(i)
        elif text_matches(["log", 'analysis']):
            for i in ["of"]:
                yield Completion(i)
        elif text_matches(["of"]):
            for i in ["current", 'last']:
                yield Completion(i)
        elif text_matches(["last", "current"]):
            for i in ["hour", "day", "week", "month", "year"]:
                yield Completion(i)
        elif text_matches(["get"]):
            for i in ["model"]:
                yield Completion(i)
        elif text_matches(["model"]):
            for i in ["parameter"]:
                yield Completion(i)
        else:
            for i in range(len(words)):
                if i != (len(words) - 1) and text_matches(words[i]):
                    for c in words[i + 1]:
                        yield Completion(c)
                    break

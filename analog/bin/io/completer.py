from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.completion import Completion, Completer
import re
from itertools import chain
from functools import partial


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

        def match_str_by_index(match_word, index):
            assert isinstance(match_word, str) or isinstance(match_word, list)
            command_list = text_before_cursor.split()
            if len(command_list) - 1 >= index:
                if isinstance(match_word, str):
                    return match_word.strip() == command_list[index]
                elif isinstance(match_word, list):
                    return len(list(filter(partial(match_str_by_index, index=index), match_word))) > 0
            return False

        def word_matches(word):
            """ True when the word before the cursor matches. """
            if self.ignore_case:
                word = word.lower()

            if self.match_middle:
                return word_before_cursor in word
            else:
                return word.startswith(word_before_cursor)

        def pre_str_match(match_word: list):
            for c in match_word:
                if self.ignore_case:
                    c = c.lower()
                str_before_cursor = text_before_cursor[document.find_previous_word_beginning(WORD=True):].lower()
                str_before_cursor.strip()
                if str_before_cursor.strip() != str_before_cursor and str_before_cursor.strip().lower() == c:
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
        elif pre_str_match(["show"]):
            for i in ['statistics', 'log', 'analysis']:
                yield Completion(i)
        elif pre_str_match(["statistics"]):
            for i in ['requests', 'IP', 'UA', 'url']:
                yield Completion(i)
        elif pre_str_match(["set"]):
            for i in ["date", "offset", "hour", "day", "month", "year"]:
                yield Completion(i)
        elif pre_str_match(['log']):
            for i in ["current", "of"]:
                yield Completion(i)
        elif match_str_by_index("log", 1) and pre_str_match(['of']):
            for i in ["ip"]:
                yield Completion(i)
        elif not match_str_by_index("locate", 0) and not match_str_by_index("log", 1) and pre_str_match(
                ['analysis', 'requests', 'IP', 'UA', 'url']):
            for i in ["current"]:
                yield Completion(i)
        elif pre_str_match(["current"]):
            for i in ["hour", "day", "week", "month", "year"]:
                yield Completion(i)
        elif pre_str_match(["get"]):
            for i in ["time", "offset", "progress", "model"]:
                yield Completion(i)
        elif pre_str_match(["current"]):
            for i in ["hour", "day", "week", "month", "year"]:
                yield Completion(i)
        elif pre_str_match(["locate"]):
            for i in ["ip"]:
                yield Completion(i)
        elif match_str_by_index("statistics", 1) and match_str_by_index(['IP', 'UA', 'url'], 2) and pre_str_match(
                ["hour", "day", "week", "month", "year"]):
            for i in ["top"]:
                yield Completion(i)
        else:
            pass

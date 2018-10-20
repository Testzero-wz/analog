import colorama
from colorama import Fore, Style, Back
import platform
import sys
import os


class ColorOutput():
    Fore = Fore
    Back = Back
    Style = Style


    def __init__(self):
        colorama.init()
        self.lastInLine = False
        self.terminal_size = self.__get_terminal_size()
        self.system = platform.system()
        self.save = None


    def __get_terminal_size(self):
        try:
            columns = os.get_terminal_size().columns
        except Exception:
            columns = 100
        return columns


    def print_info(self, message, **kwargs):
        symbol = kwargs.get('symbol') if 'symbol' in kwargs.keys() else "*"
        if self.system == "Windows":
            self.new_line(Fore.LIGHTYELLOW_EX + Style.NORMAL + "[" + symbol + "] {0}".format(message) + Style.RESET_ALL,
                          **kwargs)
        else:
            self.new_line(Fore.LIGHTGREEN_EX + Style.NORMAL + "[" + symbol + "] {0}".format(message) + Style.RESET_ALL,
                          **kwargs)


    def print_warning(self, message, **kwargs):
        self.new_line(Fore.LIGHTYELLOW_EX + '[!] {0}'.format(message) + Style.RESET_ALL, **kwargs)


    def print_error(self, message, **kwargs):
        self.new_line(Fore.RED + '[-] {0}'.format(message) + Style.RESET_ALL, **kwargs)


    def print_special(self, message, **kwargs):
        self.new_line(Fore.LIGHTMAGENTA_EX + '[*] {0}'.format(message) + Style.RESET_ALL, **kwargs)


    def print_lastLine(self, message):

        self.inLine(Fore.LIGHTYELLOW_EX + '[~] {0}'.format(message).ljust(self.terminal_size - 5, " "))


    def print_progress(self, present, url, char="~"):
        self.inLine(
                Fore.LIGHTYELLOW_EX + '[' + char \
                + '] {:2.1f}% [{:<50}] {}'.format(present if present < 100 else 99.9, "=" * int(present // 2) + (
                    ">" if present < 100 else ""), url).ljust(self.terminal_size - 5, " "))


    def print_info_green(self, message):
        self.new_line(Fore.GREEN + '[*] {0}'.format(message) + Style.RESET_ALL)


    def print_history(self, res, url):
        mes = ""
        history_res = res.history[0]
        mes += str(history_res.status) + " - " + Fore.LIGHTMAGENTA_EX + str(
                url) + Fore.GREEN + " => "
        mes += ScanOutput.get_status_color(res.status) + Fore.GREEN + " - " + Fore.LIGHTMAGENTA_EX + str(
                res.url) + Style.RESET_ALL
        self.print_info_green(mes)


    def print_changed(self, variable, value):
        self.new_line(Fore.LIGHTYELLOW_EX + Style.NORMAL + '[*] {0} was set to {1}'.format(
                Fore.LIGHTBLUE_EX + variable + Fore.LIGHTYELLOW_EX,
                Fore.LIGHTBLUE_EX + str(value)) + Style.RESET_ALL)


    def inLine(self, string):
        if len(string) > self.terminal_size:
            string = string[:self.terminal_size - 7] + "..." + Style.RESET_ALL
        string = string + "\r"
        sys.stdout.write(string)
        sys.stdout.flush()
        self.lastInLine = True


    def new_line(self, message, nowrap=False, **kwargs):
        if self.lastInLine:
            self.erase()

        if self.system == 'Windows':
            sys.stdout.write(message)
            sys.stdout.flush()

        else:
            sys.stdout.write(message)

        if not nowrap:
            sys.stdout.write('\n')

        sys.stdout.flush()
        self.lastInLine = False


    def erase(self):
        if self.system == 'Windows':
            sys.stdout.write(Style.RESET_ALL + '\r' + ' ' * (self.terminal_size - 2) + '\r')
            sys.stdout.flush()

        else:
            sys.stdout.write('\033[1K')
            sys.stdout.write('\033[0G')
            sys.stdout.flush()


    def print_banner(self, message="Default banner"):
        self.new_line(Fore.LIGHTMAGENTA_EX + " " * 10 + message + Style.RESET_ALL)
        self.new_line(Fore.LIGHTYELLOW_EX + " " * 10 + "Blog: <https://www.wzsite.cn>" + Style.RESET_ALL)
        self.new_line(Fore.LIGHTYELLOW_EX + " " * 10 + "Email: <testzero.wz@gmail.com>\n\n" + Style.RESET_ALL)


    def print_split_line(self, char="-", color='Y', message="", style=1):
        total_len = self.terminal_size
        for c in message:
            if is_chinese(c):
                total_len -=1

        if style == 1:
            self.new_line(
                    Fore.BLACK + Back.CYAN + "\n" + (" " * 4 + message).ljust(total_len,
                                                                              " ") + Style.RESET_ALL)
        else:
            margin = 20
            if color == 'Y':
                self.new_line(Fore.YELLOW + char * (total_len - len(message) - margin) + \
                              ("[" + Fore.RED + message + Style.RESET_ALL + Fore.YELLOW + "]" + char * (
                                      margin - 2) + Style.RESET_ALL if message != "" else "")
                              )
            elif color == "G":
                self.new_line(Fore.GREEN + char * (total_len - len(message) - margin) + \
                              ("[" + Fore.RED + message + Style.RESET_ALL + Fore.GREEN + "]" + char * (
                                      margin - 2) + Style.RESET_ALL if message != "" else "")
                              )
            elif color == "B":
                self.new_line(Fore.BLUE + char * (total_len - len(message) - margin) + \
                              ("[" + Fore.YELLOW + message + Style.RESET_ALL + Fore.BLUE + "]" + char * (
                                      margin - 2) + Style.RESET_ALL if message != "" else "")
                              )
            elif color == "W":
                self.new_line(Fore.WHITE + char * (total_len - len(message) - margin) + \
                              ("[" + Fore.BLUE + message + Style.RESET_ALL + Fore.WHITE + "]" + char * (
                                      margin - 2) + Style.RESET_ALL if message != "" else "")
                              )
            elif color == "R":
                self.new_line(Fore.RED + char * (total_len - len(message) - margin) + \
                              ("[" + Fore.BLUE + message + Style.RESET_ALL + Fore.RED + "]" + char * (
                                      margin - 2) + Style.RESET_ALL if message != "" else "")
                              )
            else:
                self.new_line(Fore.YELLOW + char * (total_len - len(message) - margin) + \
                              ("[" + Fore.RED + message + Style.RESET_ALL + Fore.YELLOW + "]" + char * (
                                      margin - 2) + Style.RESET_ALL if message != "" else "")
                              )


def is_chinese(char):
    return '\u4e00' <= char <= '\u9fa5'


def redirect_to_file(self, file):
    self.save = sys.stdout
    sys.stdout = file


def redirect_to_sys(self):
    sys.stdout = self.save


if __name__ == "__main__":
    pass

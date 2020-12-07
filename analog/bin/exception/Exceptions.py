class DatabaseException(Exception):
    pass


class DatabaseConfigError(DatabaseException):
    pass


class DatabaseConnectError(DatabaseException):
    pass


class RuntimeException(Exception):
    pass


class UpdateLogThreadException(RuntimeException):
    pass


class CommandFormatError(RuntimeException):
    pass


class FileException(Exception):
    pass


class FileNotFound(FileException):
    pass


class FileEmptyError(FileException):
    pass


class AddCommandError(CommandFormatError):
    pass

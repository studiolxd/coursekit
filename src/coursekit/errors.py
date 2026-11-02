"""The base of the errors coursekit explains to the person: the command line prints the message and exits with 1, without a
traceback. Every module that raises one defines its own subclass; the command line catches the base, so it need not import them."""


class CoursekitError(Exception):
    pass

"""Implements a distutils command 'build_antlr'."""

from distutils.core import Command
from os.path import join
from subprocess import check_call, CalledProcessError
from antlr_distutils import __path__


class build_antlr(Command):

    description = 'generate a parser based on ANTLR'

    user_options = [
        ('build-lib=', 'd', "directory to \"build\" (copy) to"),
        ('grammar=', 'g', "grammar to build parser for"),
        ('listener', None, "generate parse tree listener [default]"),
        ('no-listener', None, "don't generate parse tree listener"),
        ('visitor', None, "generate parse tree visitor"),
        ('no-visitor', None, "don't generate parse tree visitor [default]")
        ]

    boolean_options = ['listener', 'no-listener', 'visitor', 'no-visitor']
    # TODO: check if negative options are working
    negative_opt = {'no-listener': 'listener', 'no-visitor': 'visitor'}

    def initialize_options(self):
        self.build_lib = None
        self.grammar = None
        self.listener = None
        self.visitor = None

    def finalize_options(self):
        # Find out the build directories, ie. where to install from.
        self.set_undefined_options('build', ('build_lib', 'build_lib'))
        # TODO: assert if grammar isn't specified; should we search for a grammar?
        if self.grammar is None:
            self.grammar = 'hello/dsl/Hello.g4'
        if self.listener is None:
            self.listener = True
        if self.visitor is None:
            self.visitor = True

    def run(self):
        # TODO: check that the "JAVA_HOME" environment variable has been set and that it points to a directory
        # containing a "bin" directory and that the "bin" directory contains an executable "java" command.

        # TODO: check that the "java" command found via a search of "PATH" is the one that was found in step 1.

        # TODO: run the "java" command with "-version" to see if the output looks like a normal Java version stamp.

        # TODO: search antlr jar
        antlr_jar = join(__path__[0], 'lib/antlr-4.5.2-complete.jar')

        # TODO: determine python package name and create __init__ file

        # TODO: create java call list based on user options
        try:
            # TODO: should stdout and stderror handled in a different way?
            check_call(['java', '-jar', antlr_jar, '-o', self.build_lib, '-listener',
                        '-visitor', '-Dlanguage=Python3', self.grammar])
        except CalledProcessError:
            exit(1)

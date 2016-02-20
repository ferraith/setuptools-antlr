"""Implements the Distutils 'build' command."""

from distutils.core import Command
from os import path
from subprocess import check_call, CalledProcessError


class build_antlr(Command):

    description = "generate parser based on ANTLR"

    user_options = [
        ('build-lib=', 'd', "directory to \"build\" (copy) to"),
        ('build-parser=', 'b', "directory to build parser to"),
        ('grammar=', 'g', "grammar to build parser for"),
        ]

    boolean_options = ['force', 'listener', 'visitor']
    negative_opt = {'no-listener': 'listener', 'no-visitor': 'visitor'}

    def initialize_options(self):
        self.build_lib = None
        self.build_parser = None
        self.grammar = None
        self.listener = None
        self.visitor = None

    def finalize_options(self):
        # Find out the build directories, ie. where to install from.
        self.set_undefined_options('build',
                                   ('build_lib', 'build_lib'),
                                   ('force', 'force'))
        if self.build_parser is None:
            self.build_parser = path.join(self.build_lib, 'parser')
        if self.grammar is None:
            self.grammar = 'grammar.g4'

    def run(self):
        try:
            check_call(['java', '-jar', 'lib/antlr-4.5.2-complete.jar', '-o', self.build_parser, '-listener',
                        '-visitor', '-Dlanguage=Python3', self.grammar])
        except CalledProcessError:
            exit(1)

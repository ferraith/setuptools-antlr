"""Implements a distutils command 'build_antlr'."""

from distutils.core import Command
from os import environ
from os.path import join
from re import compile
from shutil import which
from subprocess import check_call, CalledProcessError, run, PIPE, STDOUT
from antlr_distutils import __path__

ANTLR_JAR = 'antlr-4.5.2-complete.jar'
MIN_JAVA_VERSION = {'major': 1, 'minor': 6, 'patch': 0, 'build': 0}


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

    def _find_java(self):
        # First check if a working Java is in JAVA_HOME
        if 'JAVA_HOME' in environ:
            java_bin_dir = join(environ['JAVA_HOME'], 'bin')
            java_exe = which('java', path=java_bin_dir)
            if self._validate_java(java_exe):
                return java_exe

        # If Java wasn't found in JAVA_HOME fallback to PATH
        java_exe = which('java', path=None)
        if self._validate_java(java_exe):
            return java_exe

        # Java wasn't found on the system
        return None

    def _validate_java(self, executable):
        result = run([executable, '-vesion'], stdout=PIPE, stderr=STDOUT, universal_newlines=True)

        if result.returncode == 0:
            version_regex = compile('(\d+).(\d+).(\d+)_(\d+)')

            # Get major and minor release
            version_match = version_regex.search(result.stdout)
            major = int(version_match.group(1))
            minor = int(version_match.group(2))

            # Check if Java has at least minimum required version
            if major >= MIN_JAVA_VERSION['major'] and minor >= MIN_JAVA_VERSION['minor']:
                return True

        return False

    def run(self):
        java_exe = self._find_java()
        assert java_exe is not None, "No compatible JRE was found on the system."

        # TODO: search antlr jar
        antlr_jar = join(__path__[0], 'lib', ANTLR_JAR)

        # TODO: determine python package name and create __init__ file

        # TODO: create java call list based on user options
        try:
            # TODO: should stdout and stderror handled in a different way?
            check_call([java_exe, '-jar', antlr_jar, '-o', self.build_lib, '-listener',
                        '-visitor', '-Dlanguage=Python3', self.grammar])
        except CalledProcessError:
            exit(1)

"""Implements a distutils command 'build_antlr'."""

from distutils.core import Command
from distutils.version import LooseVersion
from os import environ, listdir
from os.path import isfile, join
from re import compile
from shutil import which
from subprocess import run, PIPE, STDOUT
from antlr_distutils import __path__


class build_antlr(Command):
    _MIN_JAVA_VERSION = '1.6.0'
    _EXT_LIB_DIR = 'lib'

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
        # TODO: instead of asserting search for all root grammars
        assert self.grammar is not None, 'No grammar passed to build_antlr command.'
        if self.listener is None:
            self.listener = True
        if self.visitor is None:
            self.visitor = True

    def _find_java(self):
        # First check if a working Java is set in JAVA_HOME
        if 'JAVA_HOME' in environ:
            java_bin_dir = join(environ['JAVA_HOME'], 'bin')
            java_exe = which('java', path=java_bin_dir)
            if java_exe and self._validate_java(java_exe):
                return java_exe

        # If Java wasn't found in JAVA_HOME fallback to PATH
        java_exe = which('java', path=None)
        if java_exe and self._validate_java(java_exe):
            return java_exe

        # Java wasn't found on the system
        return None

    def _validate_java(self, executable):
        result = run([executable, '-version'], stdout=PIPE, stderr=STDOUT, universal_newlines=True)

        if result.returncode == 0:
            version_regex = compile('\d+(.\d+){2}(_\d+)?')
            version_match = version_regex.search(result.stdout)

            if version_match:
                # Create normalized versions containing only valid chars
                validated_version = LooseVersion(version_match.group(0).replace('_', '.'))
                min_version = LooseVersion(self._MIN_JAVA_VERSION.replace('_', '.'))

                return validated_version >= min_version

        return False

    def find_antlr(self):
        antlr_jar_path = join(__path__[0], self._EXT_LIB_DIR)
        antlr_jar_regex = compile('^antlr-\d+(.\d+){1,2}-complete.jar$')
        # Search for all _files_ matching regex in antlr_jar_path
        antlr_jar_matches = [element for element in listdir(antlr_jar_path) if isfile(join(antlr_jar_path, element)) and
                             antlr_jar_regex.match(element) is not None]
        if antlr_jar_matches:
            # If more than one antlr jar was found return path of the first one
            antlr_jar = join(antlr_jar_path, antlr_jar_matches[0])
            return antlr_jar
        else:
            return None

    def run(self):
        java_exe = self._find_java()
        assert java_exe is not None, "No compatible JRE was found on the system."

        antlr_jar = self.find_antlr()
        assert antlr_jar is not None, "No antlr jar was found in directory for external libraries."

        # TODO: determine python package name and create __init__ file

        # TODO: create java call list based on user options

        # TODO: should stdout and stderror handled in a different way?
        run([java_exe, '-jar', antlr_jar, '-o', self.build_lib, '-listener', '-visitor', '-Dlanguage=Python3', self.grammar])

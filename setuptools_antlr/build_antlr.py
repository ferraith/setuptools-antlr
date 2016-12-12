"""Implements the setuptools command 'build_antlr'."""
import distutils.errors
import distutils.log
import distutils.version
import operator
import os.path
import pathlib
import re
import shutil
import subprocess
import typing

import setuptools

from setuptools_antlr import __path__


class AntlrGrammar(object):
    """Basic information about an ANTLR grammar file.

    For generation of ANTLR based parsers basic information about the grammar like imports is
    necessary. This information and the functionality to retrieve this information out of a grammar
    file is placed in this class.
    """

    def __init__(self, path: pathlib.Path):
        """Initializes a new AntlrGrammar object.

        :param path: path to grammar file
        """
        # by convention grammar name is always equal to file name
        self.name = path.stem
        self.path = path
        self.dependencies = []

    def read_imports(self) -> typing.List[str]:
        """Reads all imported grammars out of grammar file.

        :return: a list of imported grammars
        """
        import_stmt_regex = re.compile('import(.*);')

        try:
            with self.path.open() as f:
                match = import_stmt_regex.search(f.read())
                if match:
                    imported_grammars = match.group(1)
                    return [s.strip() for s in imported_grammars.split(',')]
                else:
                    return []
        except IOError as e:
            raise distutils.errors.DistutilsFileError('Can\'t read grammar "{}"'.format(e.filename))

    def walk(self):
        for d in self.dependencies:
            yield d
            yield from d.walk()


class ImportGrammarError(Exception):
    """Raised when an imported grammar can't be found in package source directory."""

    def __init__(self, name: str, parent: AntlrGrammar = None):
        """Initializes a new ImportGrammarError object.

        :param name: name of included grammar
        :param parent: parent grammar which includes missing grammar
        """
        self.name = name
        self.parent = parent

    def __str__(self):
        """Returns a nicely printable string representation of this ImportGrammarError object.

        :return: a string representation of this error
        """
        return self.name


class build_antlr(setuptools.Command):
    """A setuptools command for generating ANTLR based parsers.

    An extra command for setuptools to generate ANTLR based parsers, lexers, listeners and visitors.
    The build_antlr command wraps the Java based generator provided by ANTLR developers. It
    searches for all grammar files and generates a Python package containing a modules specified in
    the user options. Please keep in mind that only grammars are generated which aren't included by
    other grammars. This prevents generation of shared content like common terminals.

    :cvar _MIN_JAVA_VERSION: Minimal version of java required by ANTLR
    :cvar _EXT_LIB_DIR: Relative path to external libs directory
    :cvar _GRAMMAR_FILE_EXT: File extension of ANTLR grammars
    :cvar description: Description of build_antlr command
    :cvar user_options: Options which can be passed by the user
    :cvar boolean_options: Subset of user options which are binary
    :cvar negative_opt: Dictionary of user options which exclude each other
    """

    _MIN_JAVA_VERSION = '1.6.0'

    _EXT_LIB_DIR = 'lib'

    _GRAMMAR_FILE_EXT = 'g4'

    description = 'generate a parser based on ANTLR'

    user_options = [
        ('build-lib=', 'd', 'directory to "build" (copy) to'),
        ('listener', None, 'generate parse tree listener [default]'),
        ('no-listener', None, 'don\'t generate parse tree listener'),
        ('visitor', None, 'generate parse tree visitor'),
        ('no-visitor', None, 'don\'t generate parse tree visitor [default]')
    ]

    boolean_options = ['listener', 'no-listener', 'visitor', 'no-visitor']

    negative_opt = {'no-listener': 'listener', 'no-visitor': 'visitor'}

    def initialize_options(self):
        """Sets default values for all the options that this command supports. Note that these
        defaults may be overridden by other commands, by the setup script, by config files, or by
        the command-line.
        """
        self.build_lib = None
        self.listener = None
        self.visitor = None

    def finalize_options(self):
        """Sets final values for all the options that this command supports. This is always called
        as late as possible, ie. after any option assignments from the command-line or from other
        commands have been done.
        """
        # find out the build directories, ie. where to install from
        self.set_undefined_options('build', ('build_lib', 'build_lib'))

    def _find_java(self) -> pathlib.Path:
        """Searches for a working Java Runtime Environment (JRE) set in JAVA_HOME or PATH
        environment variables. A JRE located in JAVA_HOME will be preferred.

        :return: a path to a working JRE or None if no JRE was found
        """
        # first check if a working Java is set in JAVA_HOME
        if 'JAVA_HOME' in os.environ:
            java_bin_dir = os.path.join(os.environ['JAVA_HOME'], 'bin')
            java_exe = shutil.which('java', path=java_bin_dir)
            if java_exe and self._validate_java(java_exe):
                return pathlib.Path(java_exe)

        # if Java wasn't found in JAVA_HOME fallback to PATH
        java_exe = shutil.which('java', path=None)
        if java_exe and self._validate_java(java_exe):
            return pathlib.Path(java_exe)

        # java wasn't found on the system
        return None

    def _validate_java(self, executable: str) -> bool:
        """Validates a Java Runtime Environment (JRE) if it fulfills minimal version required by
        ANTLR.

        :param executable: Java executable of JRE
        :return: flag whether JRE is at minimum required version
        """
        result = subprocess.run([executable, '-version'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)

        if result.returncode == 0:
            version_regex = re.compile('\d+(?:.\d+){2}(?:_\d+)')
            version_match = version_regex.search(result.stdout)

            if version_match:
                # create normalized versions containing only valid chars
                validated_version = distutils.version.LooseVersion(version_match.group(0).replace('_', '.'))
                min_version = distutils.version.LooseVersion(self._MIN_JAVA_VERSION.replace('_', '.'))

                return validated_version >= min_version

        return False

    def _find_antlr(self) -> pathlib.Path:
        """Searches for ANTLR library at setuptools-antlr install location.

        :return: a path to latest ANTLR library or None if library wasn't found
        """
        antlr_jar_path = pathlib.Path(__path__[0], self._EXT_LIB_DIR)
        antlr_jar_regex = re.compile('^antlr-(\d+(?:.\d+){1,2})-complete.jar$')

        # search for all _files_ matching regex in antlr_jar_path
        antlr_jars = []
        for antlr_jar in antlr_jar_path.iterdir():
            match = antlr_jar_regex.search(antlr_jar.name)
            if antlr_jar_path.joinpath(antlr_jar).is_file() and match:
                version = distutils.version.StrictVersion(match.group(1))
                antlr_jars.append((antlr_jar, version))

        if antlr_jars:
            # if more than one antlr jar was found return path of the latest version
            latest_antlr_jar = max(antlr_jars, key=operator.itemgetter(1))[0]
            return pathlib.Path(antlr_jar_path, latest_antlr_jar)
        else:
            return None

    def _find_grammars(self, base_path: pathlib.Path=pathlib.Path('.')) -> typing.List[AntlrGrammar]:
        """Searches for all ANTLR grammars in package source directory and returns a list of it.
        Only grammars which aren't included by other grammars are part of this list.

        :param base_path: base path to search for ANTLR grammars
        :return: a list of all found ANTLR grammars
        """
        grammars = []

        def get_grammar(name: str) -> AntlrGrammar:
            """Searches in grammars list for a grammar which has passed name.

            :param name: name of grammar
            :return: an ANTLR grammar
            """
            try:
                return next(g for g in grammars if g.name == name)
            except StopIteration:
                raise ImportGrammarError(name)

        # search for all grammars in package source directory
        for root, _, files in os.walk(str(base_path), followlinks=True):
            grammar_files = [f for f in files if f.endswith("." + self._GRAMMAR_FILE_EXT)]
            for fb in grammar_files:
                grammars.append(AntlrGrammar(pathlib.Path(root, fb)))

        # generate a dependency tree for each grammar
        grammar_tree = []
        try:
            for grammar in grammars:
                imports = grammar.read_imports()
                if imports:
                    try:
                        grammar.dependencies = [get_grammar(i) for i in imports]
                    except ImportGrammarError as e:
                        e.parent = grammar
                        raise
        except ImportGrammarError as e:
            raise distutils.errors.DistutilsFileError('Imported grammar "{}" in file "{}" isn\'t present in package '
                                                      'source directory.'.format(str(e), str(e.parent.path)))
        else:
            # remove all grammars which aren't the root of a dependency tree
            grammar_tree[:] = filter(lambda r: all(r not in g.dependencies for g in grammars),
                                     grammars)

        return grammar_tree

    @classmethod
    def _camel_to_snake_case(cls, s):
        """Converts a camel cased to a snake cased string.
        :param s: a camel cased string
        :return: a snake cased string
        """
        snake_cased = re.sub('([a-z0-9])([A-Z])', r'\1_\2', re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)).lower()
        return snake_cased.replace('__', '_')

    def run(self):
        """Performs all tasks necessary to generate ANTLR based parsers for all found grammars. This
        process is controlled by the user options passed on the command line or set internally to
        default values.
        """
        java_exe = self._find_java()
        if not java_exe:
            raise distutils.errors.DistutilsExecError('no compatible JRE was found on the system')

        antlr_jar = self._find_antlr()
        if not antlr_jar:
            raise distutils.errors.DistutilsExecError('no ANTLR jar was found in lib directory')

        grammars = self._find_grammars()

        for grammar in grammars:
            # setup file and folder locations for generation
            grammar_file = grammar.path.name
            grammar_dir = grammar.path.parent
            package_dir = pathlib.Path(self.build_lib, grammar_dir, self._camel_to_snake_case(grammar.name))

            # determine location of dependencies e.g. imported grammars and token files
            library_dir = None
            dependency_dirs = set(g.path.parent for g in grammar.walk())
            if len(dependency_dirs) == 1:
                library_dir = dependency_dirs.pop()
            elif len(dependency_dirs) > 1:
                raise distutils.errors.DistutilsOptionError('Imported grammars of \'{}\' are located in more than one '
                                                            'directory. This isn\'t supported by ANTLR. Move all '
                                                            'imported grammars into one'
                                                            'directory.'.format(grammar.name))

            run_args = [str(java_exe)]
            run_args.extend(['-jar', str(antlr_jar)])
            run_args.extend(['-o', str(package_dir.absolute())])

            if library_dir:
                run_args.extend(['-lib', str(library_dir.absolute())])

            if self.listener is not None:
                run_args.append('-listener' if self.listener == 1 else '-no-listener')
            if self.visitor is not None:
                run_args.append('-visitor' if self.visitor == 1 else '-no-visitor')

            run_args.append(str(grammar_file))

            grammar_options = ['-Dlanguage=Python3']
            if grammar_options:
                run_args.extend(grammar_options)

            run_args.append(str(grammar_file))

            # call ANTLR parser generator
            distutils.log.info('generating {} parser -> {}'.format(grammar.name, package_dir))
            try:
                subprocess.run(run_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True,
                               universal_newlines=True, cwd=str(grammar_dir))
            except subprocess.CalledProcessError as e:
                raise distutils.errors.DistutilsExecError('{} parser couldn\'t be generated\n'
                                                          '{}'.format(grammar.name, e.stdout))

            # create Python package
            init_file = pathlib.Path(package_dir, '__init__.py')
            init_file.open('wt').close()

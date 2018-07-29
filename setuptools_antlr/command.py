"""Implements the setuptools command 'antlr'."""
import collections
import datetime
import distutils.errors
import distutils.log
import distutils.version
import os.path
import pathlib
import re
import shutil
import shlex
import subprocess
import typing

import setuptools

from setuptools_antlr import __path__
from setuptools_antlr.util import camel_to_snake_case, find_java


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
        import_stmt_regex = re.compile('^\s*import\s+(.*)\s*;', re.MULTILINE)

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
        """Returns dependent grammars by walking the dependency tree of the grammar top-down."""
        for d in self.dependencies:
            yield d
            yield from d.walk()


class ImportGrammarError(Exception):
    """Raised when an imported grammar can't be found in package source directory."""

    def __init__(self, name: str, parent: AntlrGrammar=None):
        """Initializes a new ImportGrammarError object.

        :param name: name of included grammar
        :param parent: parent grammar which includes missing grammar
        """
        super().__init__()
        self.name = name
        self.parent = parent

    def __str__(self):
        """Returns a nicely printable string representation of this ImportGrammarError object.

        :return: a string representation of this error
        """
        return self.name


class AntlrCommand(setuptools.Command):
    """A setuptools command for generating ANTLR based parsers.

    An extra command for setuptools to generate ANTLR based parsers, lexers, listeners and visitors.
    The antlr command wraps the Java based generator provided by ANTLR developers. It searches for
    all grammar files and generates a Python package containing a modules specified in the user
    options. Please keep in mind that only grammars are generated which aren't included by other
    grammars. This prevents generation of shared content like common terminals.

    :cvar _MIN_JAVA_VERSION: Minimal version of java required by ANTLR
    :cvar _EXT_LIB_DIR: Relative path to external libs directory
    :cvar _GRAMMAR_FILE_EXT: File extension of ANTLR grammars
    :cvar description: Description of antlr command
    :cvar user_options: Options which can be passed by the user
    :cvar boolean_options: Subset of user options which are binary
    :cvar negative_opt: Dictionary of user options which exclude each other
    """

    _MIN_JAVA_VERSION = '1.7.0'

    _EXT_LIB_DIR = 'lib'

    _GRAMMAR_FILE_EXT = 'g4'

    description = 'generate a parser based on ANTLR'

    user_options = [
        ('grammars=', 'g', 'specify grammars to generate parsers for'),
        ('output=', 'o', 'specify directories where output is generated'),
        ('atn', None, 'generate rule augmented transition network diagrams'),
        ('encoding=', None, 'specify grammar file encoding e.g. euc-jp'),
        ('message-format=', None, 'specify output style for messages in antlr, gnu, vs2005'),
        ('long-messages', None, 'show exception details when available for errors and warnings'),
        ('listener', None, 'generate parse tree listener (default)'),
        ('no-listener', None, 'don\'t generate parse tree listener'),
        ('visitor', None, 'generate parse tree visitor'),
        ('no-visitor', None, 'don\'t generate parse tree visitor (default)'),
        ('depend', None, 'generate file dependencies'),
        ('grammar-options=', None, "set/override a grammar-level options"),
        ('w-error', None, 'treat warnings as error'),
        ('x-dbg-st', None, 'launch StringTemplate visualizer on generated code'),
        ('x-dbg-st-wait', None, 'wait for STViz to close before continuing'),
        ('x-exact-output-dir', None, 'output goes into -o directories regardless of paths/package'),
        ('x-force-atn', None, 'use the ATN simulator for all predictions'),
        ('x-log', None, 'dump lots of logging info to antlr-<timestamp>.log')
    ]

    boolean_options = ['atn', 'long-messages', 'listener', 'no-listener', 'visitor', 'no-visitor',
                       'depend', 'w-error', 'x-dbg-st', 'x-dbg-st-wait', 'x-exact-output-dir',
                       'x-force-atn', 'x-log']

    negative_opt = {'no-listener': 'listener', 'no-visitor': 'visitor'}

    def initialize_options(self):
        """Sets default values for all the options that this command supports. Note that these
        defaults may be overridden by other commands, by the setup script, by config files, or by
        the command-line.
        """
        self.grammars = None
        self.output = {}
        self.atn = 0
        self.encoding = None
        self.message_format = None
        self.long_messages = 0
        self.listener = 1
        self.visitor = 0
        self.depend = 0
        self.grammar_options = {}
        self.w_error = 0
        self.x_dbg_st = 0
        self.x_dbg_st_wait = 0
        self.x_exact_output_dir = 0
        self.x_force_atn = 0
        self.x_log = 0

    def finalize_options(self):
        """Sets final values for all the options that this command supports. This is always called
        as late as possible, ie. after any option assignments from the command-line or from other
        commands have been done.
        """
        # parse grammars
        if self.grammars:
            self.grammars = shlex.split(self.grammars, comments=True)

        # parse output option
        if self.output:
            tokens = shlex.split(self.output, comments=True)
            self.output = dict(t.split('=', 1) for t in tokens)
        # if default directory isn't specified set base directory as default
        if 'default' not in self.output:
            self.output['default'] = '.'

        # parse grammar-level options
        if self.grammar_options:
            tokens = shlex.split(self.grammar_options, comments=True)
            self.grammar_options = dict(t.split('=', 1) for t in tokens)

        # sanity check in case target language is explicitly passed by user
        if 'language' in self.grammar_options:
            if self.grammar_options['language'] != 'Python3':
                raise distutils.errors.DistutilsOptionError('{} isn\'t a supported language. Only '
                                                            'Python3 code can be generated.'.format(
                                                                self.grammar_options['language']))
        else:
            self.grammar_options['language'] = 'Python3'

        # sanity check for debugging options
        if not self.x_dbg_st and self.x_dbg_st_wait:
            distutils.log.warn('Waiting for StringTemplate visualizer (x_dbg_st_wait) without '
                               'launching it on generated code is enabled (x_dbg_st). Launching of '
                               'StringTemplate visualizer will be forced.')
            self.x_dbg_st = 1

    def _find_antlr(self) -> pathlib.Path:
        """Searches for ANTLR library at setuptools-antlr install location.

        :return: a path to latest ANTLR library or None if library wasn't found
        """
        AntlrJar = collections.namedtuple('AntlrJar', ['file', 'version'])
        antlr_jar_path = pathlib.Path(__path__[0], self._EXT_LIB_DIR)
        antlr_jar_regex = re.compile('^antlr-(\d+(?:.\d+){1,2})-complete.jar$')

        # search for all _files_ matching regex in antlr_jar_path
        antlr_jars = []
        for antlr_jar in antlr_jar_path.iterdir():
            match = antlr_jar_regex.search(antlr_jar.name)
            if antlr_jar_path.joinpath(antlr_jar).is_file() and match:
                version = distutils.version.StrictVersion(match.group(1))
                antlr_jars.append(AntlrJar(antlr_jar, version))

        if antlr_jars:
            # if more than one antlr jar was found return path of the latest version
            latest_antlr_jar = max(antlr_jars, key=lambda x: x.version)
            return pathlib.Path(antlr_jar_path, latest_antlr_jar.file)
        else:
            return None

    @classmethod
    def _find_antlr_log(cls, log_path: pathlib.Path) -> pathlib.Path:
        """Searches for ANTLR log files at passed location.

        :return: a path to the latest ANTLR log file or None if no log file was found
        """
        AntlrLog = collections.namedtuple('AntlrLog', ['file', 'timestamp'])
        antlr_log_regex = re.compile('^antlr-(\d{4}-\d{2}-\d{2}-\d{2}.\d{2}.\d{2}).log$')

        # search for all _files_ matching regex in antlr_log_regex
        antlr_logs = []
        for log_file in log_path.iterdir():
            match = antlr_log_regex.search(log_file.name)
            if log_file.is_file() and match:
                timestamp = datetime.datetime.strptime(match.group(1), '%Y-%m-%d-%H.%M.%S')
                antlr_logs.append(AntlrLog(log_file, timestamp))

        if antlr_logs:
            # if more than one antlr log was found return path of the latest log file
            latest_antlr_log = max(antlr_logs, key=lambda x: x.timestamp)
            return latest_antlr_log.file
        else:
            return None

    def _find_grammars(self, base_path: pathlib.Path=pathlib.Path('.')) -> typing.List[AntlrGrammar]:
        """Searches for all ANTLR grammars starting from base directory and returns a list of it.

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
            raise distutils.errors.DistutilsFileError('Imported grammar "{}" in file "{}" isn\'t '
                                                      'present in package source directory.'.format(
                                                          str(e), str(e.parent.path)))

        return grammars

    @classmethod
    def _create_init_file(cls, path: pathlib.Path) -> bool:
        """Creates a __init__.py file if it doesn't exist.

        :param path: path where init file should be created
        :return: True if init file was created
        """
        init_file = pathlib.Path(path, '__init__.py')
        try:
            init_file.touch(exist_ok=False)
        except FileExistsError:
            return False
        return True

    def run(self):
        """Performs all tasks necessary to generate ANTLR based parsers for all found grammars. This
        process is controlled by the user options passed on the command line or set internally to
        default values.
        """
        java_exe = find_java(self._MIN_JAVA_VERSION)
        if not java_exe:
            raise distutils.errors.DistutilsExecError('no compatible JRE was found on the system')

        antlr_jar = self._find_antlr()
        if not antlr_jar:
            raise distutils.errors.DistutilsExecError('no ANTLR jar was found in lib directory')

        # find grammars and filter result if grammars are passed by user
        grammars = self._find_grammars()
        if self.grammars:
            grammars = filter(lambda g: g.name in self.grammars, grammars)

        # generate parser for each grammar
        for grammar in grammars:
            # build up ANTLR command line
            run_args = [str(java_exe), '-jar', str(antlr_jar)]
            if self.atn:
                run_args.append('-atn')
            if self.encoding:
                run_args.extend(['-encoding', self.encoding])
            if self.message_format:
                run_args.extend(['-message-format', self.message_format])
            if self.long_messages:
                run_args.append('-long-messages')
            run_args.append('-listener' if self.listener else '-no-listener')
            run_args.append('-visitor' if self.visitor else '-no-visitor')
            if self.depend:
                run_args.append('-depend')
            run_args.extend(['-D{}={}'.format(option, value) for option, value in
                            self.grammar_options.items()])
            if self.w_error:
                run_args.append('-Werror')
            if self.x_dbg_st:
                run_args.append('-XdbgST')
            if self.x_dbg_st_wait:
                run_args.append('-XdbgSTWait')
            if self.x_exact_output_dir:
                run_args.append('-Xexact-output-dir')
            if self.x_force_atn:
                run_args.append('-Xforce-atn')
            if self.x_log:
                run_args.append('-Xlog')

            # determine location of dependencies e.g. imported grammars and token files
            dependency_dirs = set(g.path.parent for g in grammar.walk())
            if len(dependency_dirs) == 1:
                run_args.extend(['-lib', str(dependency_dirs.pop().absolute())])
            elif len(dependency_dirs) > 1:
                raise distutils.errors.DistutilsOptionError('Imported grammars of \'{}\' are '
                                                            'located in more than one directory. '
                                                            'This isn\'t supported by ANTLR. Move '
                                                            'all imported grammars into one '
                                                            'directory.'.format(grammar.name))

            # build up package path
            grammar_dir = grammar.path.parent
            if grammar.name in self.output:
                output_dir = self.output[grammar.name]
            else:
                output_dir = self.output['default']
            if self.x_exact_output_dir:
                package_dir = pathlib.Path(output_dir)
            else:
                package_dir = pathlib.Path(output_dir, grammar_dir,
                                           camel_to_snake_case(grammar.name))

            # create package directory
            package_dir.mkdir(parents=True, exist_ok=True)
            run_args.extend(['-o', str(package_dir.resolve())])

            grammar_file = grammar.path.name
            run_args.append(str(grammar_file))

            if self.depend:
                dependency_file = pathlib.Path(package_dir, 'dependencies.txt')
                distutils.log.info('generating {} file dependencies -> {}'.format(grammar_file,
                                                                                  dependency_file))

                # call ANTLR for file dependency generation
                result = subprocess.run(run_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        universal_newlines=True, cwd=str(grammar_dir))
                with dependency_file.open('wt') as f:
                    f.write(result.stdout)
            else:
                distutils.log.info('generating {} parser -> {}'.format(grammar.name, package_dir))

                # create Python package including parent packages if don't exist
                self._create_init_file(package_dir)

                base_dir = pathlib.Path('.').resolve()
                parent_dir = package_dir.resolve().parent

                while base_dir < parent_dir:
                    self._create_init_file(parent_dir)
                    parent_dir = parent_dir.parent

                # call ANTLR for parser generation
                result = subprocess.run(run_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        universal_newlines=True, cwd=str(grammar_dir))
                if result.returncode:
                    raise distutils.errors.DistutilsExecError('{} parser couldn\'t be generated\n'
                                                              '{}'.format(grammar.name,
                                                                          result.stdout))

            # move logging info into build directory
            if self.x_log:
                antlr_log_file = self._find_antlr_log(grammar_dir)
                if antlr_log_file:
                    package_log_file = pathlib.Path(package_dir, antlr_log_file.name)
                    distutils.log.info('dumping logging info of {} -> {}'.format(grammar_file,
                                                                                 package_log_file))
                    shutil.move(str(antlr_log_file), str(package_log_file))
                else:
                    distutils.log.warn('no logging info dumped out by ANTLR')

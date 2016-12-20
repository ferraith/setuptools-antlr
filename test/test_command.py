import distutils.errors
import os
import pathlib
import unittest.mock

import pytest
import setuptools.dist

from setuptools_antlr.command import AntlrGrammar, AntlrCommand


@pytest.fixture(scope='module', autouse=True)
def ch_resources_dir(request):
    os.chdir('.')
    init_dir = pathlib.Path.cwd()
    local_dir = os.path.dirname(__file__)
    os.chdir(os.path.join(local_dir, 'resources'))

    def fin():
        os.chdir(str(init_dir))
    request.addfinalizer(fin)


class TestAntlrGrammar:
    def test_read_with_imports(self):
        grammar = AntlrGrammar(pathlib.Path('distributed', 'SomeGrammar.g4'))
        imports = set(grammar.read_imports())

        assert len(imports) == 2
        assert {'CommonTerminals', 'SharedRules'} == imports

    def test_read_without_imports(self):
        grammar = AntlrGrammar(pathlib.Path('distributed', 'CommonTerminals.g4'))
        imports = grammar.read_imports()

        assert not imports

    def test_read_nonexistent_file(self):
        grammar = AntlrGrammar(pathlib.Path('FooBar.g4'))

        # check if DistutilsFileError was thrown
        with pytest.raises(distutils.errors.DistutilsFileError) as excinfo:
            grammar.read_imports()
        assert excinfo.match('FooBar.g4')


class TestAntlrCommand:
    @pytest.fixture(autouse=True)
    def command(self):
        dist = setuptools.dist.Distribution()
        return AntlrCommand(dist)

    test_ids_find_antlr = ['single', 'multiple', 'none', 'invalid']

    test_data_find_antlr = [
        ({'antlr-4.5.3-complete.jar'}, 'antlr-4.5.3-complete.jar'),
        ({'antlr-0.1.1-complete.jar', 'antlr-3.0-complete.jar', 'antlr-4.5.2-complete.jar',
          'antlr-4.5.3-complete.jar'},
         'antlr-4.5.3-complete.jar'),
        ({}, None),
        ({'antlr-runtime-4.5.3.jar'}, None)
    ]

    @pytest.mark.parametrize('available_antlr_jars, expected_antlr_jar', test_data_find_antlr,
                             ids=test_ids_find_antlr)
    def test_find_antlr(self, tmpdir, command, available_antlr_jars, expected_antlr_jar):
        ext_lib_dir = tmpdir.mkdir('lib')

        for jar in available_antlr_jars:
            antlr_jar = ext_lib_dir.join(jar)
            antlr_jar.write('dummy')

        with unittest.mock.patch.object(AntlrCommand, '_EXT_LIB_DIR', str(ext_lib_dir)):
            found_antlr_jar = command._find_antlr()

        assert found_antlr_jar == (pathlib.Path(str(ext_lib_dir), expected_antlr_jar) if expected_antlr_jar
                                   else None)

    test_ids_find_antlr_log = ['single', 'multiple', 'none', 'invalid']

    test_data_find_antlr_log = [
        ({'antlr-2016-12-19-16.01.43.log'}, 'antlr-2016-12-19-16.01.43.log'),
        ({'antlr-2016-12-18-16.01.43.log', 'antlr-2016-12-19-16.01.43.log'}, 'antlr-2016-12-19-16.01.43.log'),
        ({}, None),
        ({'foobar-2016-12-19-16.01.43.log'}, None)
    ]

    @pytest.mark.parametrize('available_antlr_logs, expected_antlr_log', test_data_find_antlr_log,
                             ids=test_ids_find_antlr_log)
    def test_find_antlr_log(self, tmpdir, command, available_antlr_logs, expected_antlr_log):
        package_dir = tmpdir.mkdir('package')

        for log in available_antlr_logs:
            antlr_log = package_dir.join(log)
            antlr_log.write('dummy')

        found_antlr_log = command._find_antlr_log(pathlib.Path(str(package_dir)))

        assert found_antlr_log == (pathlib.Path(str(package_dir), expected_antlr_log) if expected_antlr_log
                                   else None)

    def test_find_grammars_empty(self, tmpdir, command):
        dsl_dir = tmpdir.mkdir('dsl')
        g = command._find_grammars(pathlib.Path(str(dsl_dir)))

        assert len(g) == 0

    def test_find_grammars_standalone(self, command):
        g = command._find_grammars(pathlib.Path('standalone'))

        assert len(g) == 1
        assert g[0].name == 'SomeGrammar'

    def test_find_grammars_distributed(self, command):
        g = command._find_grammars(pathlib.Path('distributed'))

        assert len(g) == 1
        assert g[0].name == 'SomeGrammar'
        d = g[0].dependencies
        assert len(d) == 2
        assert d[0].name == 'CommonTerminals'
        assert d[1].name == 'SharedRules'
        dd = g[0].dependencies[0].dependencies
        assert len(dd) == 0
        dd = g[0].dependencies[1].dependencies
        assert len(dd) == 1
        assert dd[0].name == 'CommonTerminals'

    def test_find_grammars_incomplete(self, command):
        # check if DistutilsFileError was thrown
        with pytest.raises(distutils.errors.DistutilsFileError) as excinfo:
            command._find_grammars(pathlib.Path('incomplete'))
        assert excinfo.match('CommonTerminals')

    def test_finalize_options_default(self, command):
        command.finalize_options()

        assert pathlib.Path(command.build_lib) == pathlib.Path('build/lib')
        assert command.atn == 0
        assert command.encoding is None
        assert command.message_format is None
        assert command.long_messages == 0
        assert command.listener == 1
        assert command.visitor == 0
        assert command.depend == 0
        assert command.grammar_options['language'] == 'Python3'
        assert command.w_error == 0
        assert command.x_dbg_st == 0
        assert command.x_dbg_st_wait == 0
        assert command.x_force_atn == 0
        assert command.x_log == 0

    def test_finalize_options_grammar_options_language(self, command):
        command.grammar_options = 'language=Python3'
        command.finalize_options()

        assert command.grammar_options['language'] == 'Python3'

    def test_finalize_options_grammar_options_invalid(self, command):
        command.grammar_options = 'language=Java'

        with pytest.raises(distutils.errors.DistutilsOptionError) as excinfo:
            command.finalize_options()
        assert excinfo.match('Java')

    def test_finalize_options_grammar_options_multiple(self, command):
        command.grammar_options = 'superClass=Abc tokenVocab=Lexer'
        command.finalize_options()

        assert command.grammar_options['language'] == 'Python3'
        assert command.grammar_options['superClass'] == 'Abc'
        assert command.grammar_options['tokenVocab'] == 'Lexer'

    def test_finalize_options_debugging_options_invalid(self, capsys, command):
        command.x_dbg_st = 0
        command.x_dbg_st_wait = 1
        command.finalize_options()

        # check if error was logged
        _, err = capsys.readouterr()
        assert 'Waiting for StringTemplate visualizer' in err

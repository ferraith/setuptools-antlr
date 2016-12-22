import distutils.errors
import os
import pathlib
import subprocess
import unittest.mock

import pytest
import setuptools.dist

import setuptools_antlr.command
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

    @pytest.fixture()
    def configured_command(self, monkeypatch, tmpdir, command):
        command._find_antlr = unittest.mock.Mock(return_value=pathlib.Path('antlr-4.5.3-complete.jar'))
        command._find_grammars = unittest.mock.Mock(return_value=[
            AntlrGrammar(pathlib.Path('standalone/SomeGrammar.g4'))
        ])
        command.build_lib = str(tmpdir.mkdir('build_lib'))

        monkeypatch.setattr(setuptools_antlr.command, 'find_java',
                            unittest.mock.Mock(return_value=pathlib.Path('c:/path/to/java/bin/java.exe')))

        return command

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

    @unittest.mock.patch('setuptools_antlr.command.find_java')
    @unittest.mock.patch('subprocess.run')
    @unittest.mock.patch.object(AntlrCommand, '_find_grammars')
    def test_run_java_found(self, mock_find_grammars, mock_run, mock_find_java, tmpdir, command):
        java_exe = pathlib.Path('c:/path/to/java/bin/java.exe')

        mock_find_java.return_value = java_exe
        mock_find_grammars.return_value = [AntlrGrammar(pathlib.Path('standalone/SomeGrammar.g4'))]
        mock_run.return_value = subprocess.CompletedProcess([], 0)

        command.build_lib = str(tmpdir.mkdir('build_lib'))
        command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert str(java_exe) in args[0]
        assert '-jar' in args[0]

    @unittest.mock.patch('setuptools_antlr.command.find_java')
    def test_run_java_not_found(self, mock_find_java, command):
        mock_find_java.return_value = None

        with pytest.raises(distutils.errors.DistutilsExecError) as excinfo:
            command.run()
        assert excinfo.match('no compatible JRE')

    @unittest.mock.patch('setuptools_antlr.command.find_java')
    @unittest.mock.patch.object(AntlrCommand, '_find_antlr')
    @unittest.mock.patch('subprocess.run')
    @unittest.mock.patch.object(AntlrCommand, '_find_grammars')
    def test_run_antlr_found(self, mock_find_grammars, mock_run, mock_find_antlr, mock_find_java, tmpdir, command):
        java_exe = pathlib.Path('c:/path/to/java/bin/java.exe')
        antlr_jar = pathlib.Path('antlr-4.5.3-complete.jar')

        mock_find_java.return_value = java_exe
        mock_find_antlr.return_value = antlr_jar
        mock_find_grammars.return_value = [AntlrGrammar(pathlib.Path('standalone/SomeGrammar.g4'))]
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        command.build_lib = str(tmpdir.mkdir('build_lib'))
        command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert str(antlr_jar) in args[0]

    @unittest.mock.patch('setuptools_antlr.command.find_java')
    @unittest.mock.patch.object(AntlrCommand, '_find_antlr')
    def test_run_antlr_not_found(self, mock_find_antlr, mock_find_java, command):
        java_exe = pathlib.Path('c:/path/to/java/bin/java.exe')

        mock_find_java.return_value = java_exe
        mock_find_antlr.return_value = None

        with pytest.raises(distutils.errors.DistutilsExecError) as excinfo:
            command.run()
        assert excinfo.match('no ANTLR jar')

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_atn_enabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.atn = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-atn' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_atn_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.atn = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-atn' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_encoding_specified(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.encoding = 'euc-jp'
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-encoding' in args[0]
        assert 'euc-jp' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_encoding_not_specified(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.encoding = None
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-encoding' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_message_format_specified(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.message_format = 'gnu'
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-message-format' in args[0]
        assert 'gnu' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_message_format_not_specified(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.message_format = None
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-message-format' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_long_messages_enabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.long_messages = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-long-messages' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_long_messages_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.long_messages = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-long-messages' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_listener_enabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.listener = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-listener' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_listener_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.listener = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-no-listener' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_visitor_enabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.visitor = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-visitor' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_visitor_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.visitor = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-no-visitor' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_grammar_options_specified(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.grammar_options = {'superClass': 'Foo', 'tokenVocab': 'Bar'}
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-DsuperClass=Foo' in args[0]
        assert '-DtokenVocab=Bar' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_grammar_options_not_specified(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.grammar_options = {}
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert not any(a.startswith('-D') for a in args[0])

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_depend_enabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0, stdout='FooParser.py : Foo.g4')

        configured_command.depend = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-depend' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_depend_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)
        configured_command.depend = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-depend' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_w_error_enabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.w_error = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-Werror' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_w_error_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.w_error = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-Werror' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_x_dbg_st_enabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.x_dbg_st = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-XdbgST' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_x_dbg_st_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.x_dbg_st = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-XdbgST' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_x_dbg_st_wait_enabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.x_dbg_st_wait = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-XdbgSTWait' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_x_dbg_st_wait_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.x_dbg_st_wait = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-XdbgSTWait' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_x_force_atn_wait_enabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.x_force_atn = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-Xforce-atn' in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_x_force_atn_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.x_force_atn = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-Xforce-atn' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    @unittest.mock.patch.object(AntlrCommand, '_find_antlr_log')
    @unittest.mock.patch('shutil.move')
    def test_run_x_log_enabled(self, mock_move, mock_find_antlr_log, mock_run, capsys, configured_command):
        log_file = 'antlr-2016-12-19-16.01.43.log'
        mock_run.return_value = unittest.mock.Mock(returncode=0)
        mock_find_antlr_log.return_value = pathlib.Path(log_file)

        configured_command.x_log = 1
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-Xlog' in args[0]

        args, _ = mock_move.call_args
        assert mock_move.called
        assert log_file in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_x_log_disabled(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.x_log = 0
        configured_command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-Xlog' not in args[0]

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    @unittest.mock.patch.object(AntlrCommand, '_find_antlr_log')
    def test_run_x_log_not_found(self, mock_find_antlr_log, mock_run, capsys, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)
        mock_find_antlr_log.return_value = None

        configured_command.x_log = 1
        configured_command.run()

        _, err = capsys.readouterr()
        assert 'no logging info dumped out by ANTLR' in err

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_parser_generation_successful(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        configured_command.run()

        args, kwargs = mock_run.call_args
        assert mock_run.called
        assert 'SomeGrammar.g4' in args[0]
        assert kwargs['cwd'] == 'standalone'

    @pytest.mark.usefixtures('configured_command')
    @unittest.mock.patch('subprocess.run')
    def test_run_parser_generation_failed(self, mock_run, configured_command):
        mock_run.return_value = unittest.mock.Mock(returncode=-1)

        with pytest.raises(distutils.errors.DistutilsExecError) as excinfo:
            configured_command.run()
        assert excinfo.match('SomeGrammar parser couldn\'t be generated')

    @unittest.mock.patch('setuptools_antlr.command.find_java')
    @unittest.mock.patch.object(AntlrCommand, '_find_antlr')
    @unittest.mock.patch('subprocess.run')
    @unittest.mock.patch.object(AntlrCommand, '_find_grammars')
    def test_run_one_library_location(self, mock_find_grammars, mock_run, mock_find_antlr, mock_find_java, tmpdir,
                                      command):
        java_exe = pathlib.Path('c:/path/to/java/bin/java.exe')
        antlr_jar = pathlib.Path('antlr-4.5.3-complete.jar')
        mock_find_java.return_value = java_exe
        mock_find_antlr.return_value = antlr_jar

        grammar = AntlrGrammar(pathlib.Path('SomeGrammar.g4'))
        grammar.dependencies = [
            AntlrGrammar(pathlib.Path('shared/CommonTerminals.g4'))
        ]
        mock_find_grammars.return_value = [grammar]
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        command.build_lib = str(tmpdir.mkdir('build_lib'))
        command.run()

        args, _ = mock_run.call_args
        assert mock_run.called
        assert '-lib' in args[0]
        assert any(a.endswith('shared') for a in args[0])

    @unittest.mock.patch('setuptools_antlr.command.find_java')
    @unittest.mock.patch.object(AntlrCommand, '_find_antlr')
    @unittest.mock.patch('subprocess.run')
    @unittest.mock.patch.object(AntlrCommand, '_find_grammars')
    def test_run_multiple_library_location(self, mock_find_grammars, mock_run, mock_find_antlr, mock_find_java, tmpdir,
                                           command):
        java_exe = pathlib.Path('c:/path/to/java/bin/java.exe')
        antlr_jar = pathlib.Path('antlr-4.5.3-complete.jar')
        mock_find_java.return_value = java_exe
        mock_find_antlr.return_value = antlr_jar

        grammar = AntlrGrammar(pathlib.Path('SomeGrammar.g4'))
        grammar.dependencies = [
            AntlrGrammar(pathlib.Path('terminals/common.g4')),
            AntlrGrammar(pathlib.Path('rules/common.g4'))
        ]
        mock_find_grammars.return_value = [grammar]
        mock_run.return_value = unittest.mock.Mock(returncode=0)

        command.build_lib = str(tmpdir.mkdir('build_lib'))

        with pytest.raises(distutils.errors.DistutilsOptionError) as excinfo:
            command.run()
        assert excinfo.match('Imported grammars of \'SomeGrammar\' are located in more than one directory.')

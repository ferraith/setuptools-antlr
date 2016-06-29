import os
from pathlib import Path

import pytest

from antlr_distutils.build_antlr import AntlrGrammar


@pytest.fixture(scope="module", autouse=True)
def ch_resources_dir():
    localdir = os.path.dirname(__file__)
    os.chdir(os.path.join(localdir, 'resources'))


def test_antlr_grammar_read_imports():
    grammar = AntlrGrammar(Path('SomeGrammar.g4'))
    imports = set(grammar.read_imports())
    assert len(imports) == 2
    assert set(['CommonTerminals', 'SharedRules']) == imports

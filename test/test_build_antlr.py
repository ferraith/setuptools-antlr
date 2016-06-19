import os
from pathlib import Path

import pytest

from antlr_distutils.build_antlr import AntlrGrammar


@pytest.fixture(scope="module", autouse=True)
def ch_resources_dir():
    localdir = os.path.dirname(__file__)
    os.chdir(os.path.join(localdir, 'resources'))


def test_dummy():
    grammar = AntlrGrammar(Path('Hello.g4'))
    assert grammar is not None



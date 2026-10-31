"""Test the pypdf.generic._base module."""
from contextlib import nullcontext
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import Callable

import pytest

from pypdf import PdfReader
from pypdf._utils import StreamType
from pypdf.errors import PdfReadError
from pypdf.generic import IndirectObject

TESTS_ROOT = Path(__file__).parent.parent.resolve()
PROJECT_ROOT = TESTS_ROOT.parent
RESOURCE_ROOT = PROJECT_ROOT / "resources"


def _check_indirect_object_reading_limits(
        function: Callable[[StreamType], IndirectObject], should_raise: bool = True
) -> None:
    stream = BytesIO(b"42 0 R")
    obj = function(stream)
    assert obj.idnum == 42
    assert obj.generation == 0

    stream = BytesIO(b"13      37    R")
    obj = function(stream)
    assert obj.idnum == 13
    assert obj.generation == 37

    stream = BytesIO(b"2" * 64 + b" 0 R")
    obj = function(stream)
    assert obj.idnum == int("2" * 64)
    assert obj.generation == 0

    stream = BytesIO(b"10 " + b"2" * 64 + b" R")
    obj = function(stream)
    assert obj.idnum == 10
    assert obj.generation == int("2" * 64)

    stream = BytesIO(b"2" * 65)
    context = pytest.raises(
        expected_exception=PdfReadError, match=r"^Object ID exceeds maximum length limit of 64\.$"
    ) if should_raise else nullcontext()
    with context:
        obj = function(stream)
        assert obj.idnum == int("2" * 64)
        assert obj.generation == 2

    stream = BytesIO(b"2" * 100)
    with context:
        obj = function(stream)
        assert obj.idnum == int("2" * 64)
        assert obj.generation == int("2" * 35)

    stream = BytesIO(b"10  " + b"3" * 65)
    context = pytest.raises(
        expected_exception=PdfReadError, match=r"^Generation number exceeds maximum length limit of 64\.$"
    ) if should_raise else nullcontext()
    with context:
        obj = function(stream)
        assert obj.idnum == 10
        assert obj.generation == int("3" * 64)

    stream = BytesIO(b"10  " + b"3" * 99)
    with context:
        obj = function(stream)
        assert obj.idnum == 10
        assert obj.generation == int("3" * 64)

    stream = BytesIO(b"xxx 0 R")
    context = pytest.raises(
        expected_exception=PdfReadError if should_raise else ValueError,  # type: ignore[arg-type]
        match=r"^Invalid indirect object reference \(b'xxx' b'0' R\): invalid literal for int\(\) with base 10: b'xxx'$"
    )
    with context:
        obj = function(stream)
        assert obj.idnum == 10
        assert obj.generation == int("3" * 64)


def test_indirect_object__read_from_stream__limits() -> None:
    test_function = partial(IndirectObject.read_from_stream, pdf=None)
    _check_indirect_object_reading_limits(test_function)


def test_pdf_reader__read_object_header__limits(caplog: pytest.LogCaptureFixture) -> None:
    def test_function(stream: StreamType) -> IndirectObject:
        reader = PdfReader(RESOURCE_ROOT / "crazyones.pdf")
        idnum, generation = reader.read_object_header(stream)
        return IndirectObject(idnum, generation, pdf=None)

    _check_indirect_object_reading_limits(test_function, should_raise=False)

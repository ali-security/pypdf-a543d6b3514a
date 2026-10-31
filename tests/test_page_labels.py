"""Test the pypdf._page_labels module."""
from io import BytesIO
from pathlib import Path
from unittest import mock

import pytest

from pypdf import PdfReader, PdfWriter
from pypdf._page_labels import (
    get_label_from_nums,
    index2label,
    index2labels,
    number2lowercase_letter,
    number2lowercase_roman_numeral,
    number2uppercase_letter,
    number2uppercase_roman_numeral,
    nums_clear_range,
    nums_insert,
    nums_next,
)
from pypdf.errors import PdfReadError
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    FloatObject,
    IndirectObject,
    NameObject,
    NullObject,
    NumberObject,
    TextStringObject,
)

from . import get_data_from_url

TESTS_ROOT = Path(__file__).parent.resolve()
PROJECT_ROOT = TESTS_ROOT.parent
RESOURCE_ROOT = PROJECT_ROOT / "resources"


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (1, "I"),
        (2, "II"),
        (3, "III"),
        (4, "IV"),
        (5, "V"),
        (6, "VI"),
        (7, "VII"),
        (8, "VIII"),
        (9, "IX"),
        (10, "X"),
        (3_888, "MMMDCCCLXXXVIII"),
        (3_999, "MMMCMXCIX"),
    ],
)
def test_number2uppercase_roman_numeral(number, expected):
    assert number2uppercase_roman_numeral(number) == expected


def test_number2lowercase_roman_numeral():
    assert number2lowercase_roman_numeral(123) == "cxxiii"


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (1, "a"),
        (2, "b"),
        (3, "c"),
        (25, "y"),
        (26, "z"),
        (27, "aa"),
        (28, "ab"),
    ],
)
def test_number2lowercase_letter(number, expected):
    assert number2lowercase_letter(number) == expected


def test_number2uppercase_letter():
    with pytest.raises(ValueError):
        number2uppercase_letter(-1)


@pytest.mark.enable_socket
def test_index2label(caplog):
    name = "waarom-meisjes-het-beter-doen-op-HAVO-en-VWO-ROA.pdf"
    r = PdfReader(BytesIO(get_data_from_url(name=name)))
    assert index2label(r, 1) == "ii"
    assert index2label(r, 9) == "6"
    # very silly data to get test cover
    r.trailer["/Root"]["/PageLabels"]["/Nums"].append(8)
    r.trailer["/Root"]["/PageLabels"]["/Nums"].append(NullObject())
    assert index2label(r, 9) == "10"

    with pytest.raises(ValueError):
        nums_clear_range(
            NumberObject(10), 8, r.trailer["/Root"]["/PageLabels"]["/Nums"]
        )
    r.trailer["/Root"]["/PageLabels"]["/Nums"].append(8)
    with pytest.raises(ValueError):
        nums_next(NumberObject(10), r.trailer["/Root"]["/PageLabels"]["/Nums"])
    with pytest.raises(ValueError):
        nums_clear_range(
            NumberObject(10), 8, r.trailer["/Root"]["/PageLabels"]["/Nums"]
        )
    with pytest.raises(ValueError):
        nums_insert(
            NumberObject(10),
            DictionaryObject(),
            r.trailer["/Root"]["/PageLabels"]["/Nums"],
        )

    del r.trailer["/Root"]["/PageLabels"]["/Nums"]
    assert index2label(r, 1) == "2"
    caplog.clear()
    r.trailer["/Root"]["/PageLabels"][NameObject("/Kids")] = NullObject()
    assert index2label(r, 1) == "2"
    assert caplog.text != ""


@pytest.mark.enable_socket
def test_index2label_kids():
    url = "https://github.com/py-pdf/pypdf/files/14858124/Terminologie_Epochen.Schwerpunkte.Umsetzungen.pdf"
    r = PdfReader(BytesIO(get_data_from_url(url=url, name="index2label_kids.pdf")))
    expected = [
        "C1",
        "I",
        "II",
        "III",
        "IV",
        "V",
        "VI",
        "VII",
        "VIII",
        "IX",
        "X",
        "XI",
        "XII",
        "XIII",
        "XIV",
        "XV",
        "XVI",
        "XVII",
        *list(map(str, range(1, 284)))
    ]
    for x in ["20", "44", "58", "82", "94", "116", "154", "166", "192", "224", "250"]:
        # Some page labels are unused. Removing them is still easier than copying the
        # whole list itself here.
        expected.remove(x)
    assert r.page_labels == expected


@pytest.mark.enable_socket
def test_index2label_kids__recursive(caplog):
    url = "https://github.com/py-pdf/pypdf/files/14842446/tt1.pdf"
    r = PdfReader(
        BytesIO(get_data_from_url(url=url, name="index2label_kids_recursive.pdf"))
    )
    expected = [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "17",
        "18",
        "19",
    ]
    assert r.page_labels == expected
    assert caplog.text != ""


def test_get_label_from_nums__empty_nums_list():
    dictionary_object = DictionaryObject()
    dictionary_object[NameObject("/Nums")] = ArrayObject()
    assert get_label_from_nums(dictionary_object, 13) == "14"


def test_get_label_from_nums__malformed_start(caplog):
    value = DictionaryObject({
        NameObject("/S"): NameObject("/D"),
        NameObject("/St"): NameObject("/bad"),
    })
    dictionary_object = DictionaryObject()
    dictionary_object[NameObject("/Nums")] = ArrayObject([NumberObject(0), value])
    assert get_label_from_nums(dictionary_object, 3) == "4"
    assert caplog.messages == [
        (
            "Ignoring malformed page label entry in /Nums (/St='/bad', /P=''): "
            "unsupported operand type(s) for +: 'int' and 'NameObject'"
        )
    ]


def test_index2label__empty_kids_list():
    reader = PdfReader(RESOURCE_ROOT / "crazyones.pdf")
    number_tree = DictionaryObject()
    number_tree[NameObject("/Kids")] = ArrayObject()
    root = reader.root_object
    root[NameObject("/PageLabels")] = number_tree

    assert index2label(reader, 42) == "43"


def test_get_label_from_nums__roman__limits(caplog):
    with pytest.raises(expected_exception=ValueError, match=r"^Number is out of range\.$"):
        number2uppercase_roman_numeral(4321)
    assert caplog.messages == []

    labels_large = DictionaryObject({
        NameObject("/Nums"): ArrayObject([
            NumberObject(0),
            DictionaryObject({
                NameObject("/S"): NameObject("/R"),
                NameObject("/St"): NumberObject(5000)
            })
        ])
    })
    assert get_label_from_nums(labels_large, 0) == "1"
    assert caplog.messages == [
        "Ignoring malformed page label entry in /Nums (/St=5000, /P=''): Number is out of range."
    ]

    labels_negative = DictionaryObject({
        NameObject("/Nums"): ArrayObject([
            NumberObject(-10_000),
            DictionaryObject({
                NameObject("/S"): NameObject("/R"),
            })
        ])
    })
    caplog.clear()
    assert get_label_from_nums(labels_negative, 0) == "1"
    assert caplog.messages == [
        "Ignoring malformed page label entry in /Nums (/St=1, /P=''): Number is out of range."
    ]


@pytest.mark.parametrize("number", [0, -1, -1_000])
def test_number2uppercase_roman_numeral__not_positive(number):
    with pytest.raises(expected_exception=ValueError, match=r"^Expecting a positive number\.$"):
        number2uppercase_roman_numeral(number)
    with pytest.raises(expected_exception=ValueError, match=r"^Expecting a positive number\.$"):
        number2lowercase_roman_numeral(number)


@pytest.mark.timeout(10)
@pytest.mark.parametrize("style", ["/R", "/r"])
@pytest.mark.parametrize("use_kids", [False, True])
def test_index2label__roman__huge_start(caplog, style, use_kids):
    # A huge /St value must not make pypdf build a gigantic roman numeral string.
    huge_start = 10**15
    nums = ArrayObject([
        NumberObject(0),
        DictionaryObject({
            NameObject("/S"): NameObject(style),
            NameObject("/St"): NumberObject(huge_start),
        }),
    ])
    if use_kids:
        number_tree = DictionaryObject({
            NameObject("/Kids"): ArrayObject([
                DictionaryObject({
                    NameObject("/Limits"): ArrayObject([NumberObject(0), NumberObject(10)]),
                    NameObject("/Nums"): nums,
                })
            ])
        })
    else:
        number_tree = DictionaryObject({NameObject("/Nums"): nums})

    reader = PdfReader(RESOURCE_ROOT / "crazyones.pdf")
    reader.root_object[NameObject("/PageLabels")] = number_tree
    caplog.clear()

    assert index2label(reader, 0) == "1"
    assert index2label(reader, 3) == "4"
    assert caplog.messages == [
        (
            "Ignoring malformed page label entry in /Nums "
            f"(/St={huge_start}, /P=''): Number is out of range."
        ),
    ] * 2


def _build_label(*, style=None, prefix=None, start=None) -> DictionaryObject:
    entry = DictionaryObject()
    if style is not None:
        entry[NameObject("/S")] = NameObject(style)
    if prefix is not None:
        entry[NameObject("/P")] = TextStringObject(prefix)
    if start is not None:
        entry[NameObject("/St")] = NumberObject(start)
    return entry


def _outcome(function, *args):
    """
    Return the result of the call, or the type and message of the raised exception.

    ``get_label_from_nums`` of this version raises on some malformed entries
    (unknown /S style, key without value, /Nums not an array), so
    ``index2labels`` has to fail the same way as the page by page resolution.
    """
    try:
        return function(*args)
    except Exception as exception:  # noqa: BLE001
        return type(exception), str(exception)


def _labels_page_by_page(pdf, page_count):
    return [index2label(pdf, index) for index in range(page_count)]


@pytest.mark.parametrize(
    "nums",
    [
        pytest.param(
            [0, _build_label(style="/r"), 4, _build_label(style="/D"), 10, _build_label(style="/A", prefix="App-")],
            id="roman-decimal-letters-with-prefix",
        ),
        pytest.param([3, _build_label(style="/D", start=7)], id="first-key-after-first-page-with-start"),
        pytest.param(
            [0, _build_label(style="/D"), 1, _build_label(style="/R"), 2, _build_label(prefix="Cover")],
            id="prefix-without-style",
        ),
        pytest.param([0, _build_label(style="/X"), 5, _build_label(style="/D")], id="unknown-style"),
        pytest.param([0, NullObject(), 6, _build_label(style="/a")], id="value-not-a-dictionary"),
        pytest.param([8, _build_label(style="/D"), 2, _build_label(style="/r")], id="keys-not-sorted"),
        pytest.param([0, _build_label(style="/D"), 5], id="last-key-without-value"),
        pytest.param([0, _build_label(style="/D"), 0, _build_label(style="/r")], id="duplicate-keys"),
        pytest.param([40, _build_label(style="/D")], id="only-key-after-last-page"),
        pytest.param(
            [40, _build_label(style="/D"), 0, _build_label(style="/r")],
            id="first-key-after-last-page-then-smaller-key",
        ),
        pytest.param(
            [40, _build_label(style="/D"), 50, _build_label(style="/r")],
            id="first-key-after-last-page-then-larger-key",
        ),
        pytest.param(
            [key for i in range(100) for key in (i * 3, _build_label(style="/D", prefix=f"P{i}-"))],
            id="more-ranges-than-pages",
        ),
        pytest.param(
            [0, _build_label(style="/D"), 10, _build_label(style="/r"), 50],
            id="key-without-value-after-last-page",
        ),
        pytest.param(
            [0, _build_label(style="/D"), 2, _build_label(style="/r"), 1, _build_label(style="/A"),
             12, _build_label(style="/a"), 5, _build_label(style="/R", prefix="Z-")],
            id="keys-going-up-and-down",
        ),
        pytest.param(
            [FloatObject("-0.5"), _build_label(style="/D"), FloatObject("2.5"), _build_label(style="/D", prefix="F-")],
            id="float-keys",
        ),
        pytest.param([], id="empty-nums"),
    ],
)
def test_index2labels_matches_index2label(nums, caplog):
    reader = PdfReader(RESOURCE_ROOT / "crazyones.pdf")
    reader.root_object[NameObject("/PageLabels")] = DictionaryObject(
        {NameObject("/Nums"): ArrayObject(NumberObject(n) if isinstance(n, int) else n for n in nums)}
    )

    expected = _outcome(_labels_page_by_page, reader, 30)
    expected_messages = caplog.messages[:]
    caplog.clear()

    assert _outcome(index2labels, reader, 30) == expected
    assert caplog.messages == expected_messages


def test_index2labels__no_pages():
    reader = PdfReader(RESOURCE_ROOT / "crazyones.pdf")
    reader.root_object[NameObject("/PageLabels")] = NullObject()

    assert index2labels(reader, 0) == []


def test_index2labels__nums_not_an_array(caplog):
    reader = PdfReader(RESOURCE_ROOT / "crazyones.pdf")
    reader.root_object[NameObject("/PageLabels")] = DictionaryObject(
        {NameObject("/Nums"): DictionaryObject({NameObject("/A"): NumberObject(1)})}
    )
    expected = _outcome(_labels_page_by_page, reader, 3)
    expected_messages = caplog.messages[:]
    caplog.clear()

    assert _outcome(index2labels, reader, 3) == expected
    assert caplog.messages == expected_messages


@pytest.mark.parametrize(
    "number_tree",
    [
        pytest.param(None, id="no-page-labels"),
        pytest.param(
            DictionaryObject({
                NameObject("/Kids"): ArrayObject([
                    DictionaryObject({
                        NameObject("/Limits"): ArrayObject([NumberObject(0), NumberObject(40)]),
                        NameObject("/Nums"): ArrayObject([
                            NumberObject(0), _build_label(style="/r"), NumberObject(3), _build_label(style="/D"),
                        ]),
                    })
                ])
            }),
            id="kids",
        ),
        pytest.param(DictionaryObject(), id="neither-nums-nor-kids"),
    ],
)
def test_index2labels_matches_index2label__not_flat(number_tree, caplog):
    reader = PdfReader(RESOURCE_ROOT / "crazyones.pdf")
    if number_tree is not None:
        reader.root_object[NameObject("/PageLabels")] = number_tree

    expected = _outcome(_labels_page_by_page, reader, 30)
    expected_messages = caplog.messages[:]
    caplog.clear()

    assert _outcome(index2labels, reader, 30) == expected
    assert caplog.messages == expected_messages


@pytest.mark.parametrize("strict", [False, True])
def test_index2labels_matches_index2label__indirect_values(caplog, strict):
    writer = PdfWriter()
    for _ in range(30):
        writer.add_blank_page(72, 72)
    writer.root_object[NameObject("/PageLabels")] = DictionaryObject({
        NameObject("/Nums"): ArrayObject([
            NumberObject(0), writer._add_object(_build_label(style="/r")),
            NumberObject(4), writer._add_object(_build_label(style="/D", start=3)),
            NumberObject(10), NullObject(),  # Replaced by a reference to a missing object below.
            NumberObject(20), writer._add_object(_build_label(style="/A", prefix="App-")),
        ])
    })
    data = BytesIO()
    writer.write(data)

    def page_labels_of_fresh_reader(get_labels):
        reader = PdfReader(BytesIO(data.getvalue()), strict=strict)
        nums = reader.root_object["/PageLabels"]["/Nums"]
        nums[5] = IndirectObject(9999, 0, reader)
        return _outcome(get_labels, reader, len(reader.pages))

    caplog.clear()
    expected = page_labels_of_fresh_reader(_labels_page_by_page)
    expected_messages = caplog.messages[:]
    caplog.clear()

    assert page_labels_of_fresh_reader(index2labels) == expected
    assert caplog.messages == expected_messages
    assert "Object 9999 0 not defined." in expected_messages
    if strict:
        assert expected == (PdfReadError, "Could not find object.")
    else:
        assert expected[:12] == ["i", "ii", "iii", "iv", "3", "4", "5", "6", "7", "8", "11", "12"]
        assert expected[-1] == "App-J"


class _CountingArrayObject(ArrayObject):
    """``/Nums`` array which counts how often its entries are read."""

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.reads = 0

    def __getitem__(self, key):
        self.reads += 1
        return super().__getitem__(key)


@pytest.mark.parametrize(
    "keys",
    [
        pytest.param([NumberObject(key) for key in range(-500, 0)], id="increasing-keys"),
        pytest.param([NumberObject(0)] * 500, id="repeated-keys"),
        pytest.param([NumberObject(-key) for key in range(500)], id="decreasing-keys"),
        pytest.param([FloatObject(-key - 0.5) for key in range(500)], id="float-keys"),
    ],
)
@pytest.mark.parametrize("indirect_values", [False, True])
def test_page_labels__flat_nums_many_ranges_scanned_once(keys, indirect_values):
    """
    Every key of these arrays is at or below every page index, so resolving the
    pages one by one walks the whole /Nums array again for each page.
    """
    page_count = 100
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(72, 72)
    nums = _CountingArrayObject()
    for i, key in enumerate(keys):
        value = _build_label(style="/D", prefix=f"P{i}-")
        nums.extend([key, writer._add_object(value) if indirect_values else value])
    writer.root_object[NameObject("/PageLabels")] = DictionaryObject({NameObject("/Nums"): nums})
    expected = _labels_page_by_page(writer, page_count)
    nums.reads = 0

    assert writer.page_labels == expected
    assert expected[-1].startswith(f"P{len(keys) - 1}-")
    # Linear in the size of the array and the number of pages, instead of their product.
    assert nums.reads <= 3 * (len(nums) + page_count)


def test_page_labels__crafted_pdf_with_many_ranges():
    page_count = 300
    ranges = 3_000
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(72, 72)
    nums = ArrayObject()
    for i in range(ranges):
        nums.append(NumberObject(i - ranges))
        nums.append(writer._add_object(_build_label(style="/r", prefix=f"R{i}-")))
    writer.root_object[NameObject("/PageLabels")] = DictionaryObject({NameObject("/Nums"): nums})
    data = BytesIO()
    writer.write(data)

    reader = PdfReader(data)
    assert len(reader.pages) == page_count
    with mock.patch.object(reader, "get_object", wraps=reader.get_object) as get_object:
        labels = reader.page_labels

    assert labels == [f"R{ranges - 1}-{number2lowercase_roman_numeral(index + 2)}" for index in range(page_count)]
    # Each label dictionary is resolved about once, not once per page.
    assert get_object.call_count <= 2 * (ranges + page_count)

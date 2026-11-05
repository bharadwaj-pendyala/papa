import pytest

from papa.reporters.common import LineIndex


def _rescan(source: str, offset: int) -> tuple[int, int]:
    line = source.count("\n", 0, offset) + 1
    return line, offset - (source.rfind("\n", 0, offset) + 1) + 1


@pytest.mark.parametrize("source", ["", "one line", "a\nb\n", "\n\nx", "crlf\r\nline two\r\n", "é\nü ö\n"])
def test_line_index_agrees_with_a_rescan_at_every_offset(source):
    index = LineIndex(source)
    for offset in range(len(source) + 1):
        assert index.line_col(offset) == _rescan(source, offset)

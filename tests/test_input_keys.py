import random

from pyterm.term.input_keys import EscapeCodeDecoder, KEY_MAP


def test_all_keys_are_tuple():
    for key, val in KEY_MAP.items():
        assert isinstance(key, str), f"{repr(key)} not a string"
        assert isinstance(val, tuple), f"{repr(key)} value not tuple"
        assert all(
            isinstance(v, str) for v in val
        ), f"{repr(key)} sub-values not all str"


def test_escape_code_decoder():

    keys = list(KEY_MAP.keys())

    # Remove the bare escape code, because there are many ambiguous
    # cases that would otherwise cause this test to fail. We test some
    # of these cases separately.
    keys.remove("\x1b")
    keys.remove("\x1b\x1b")

    for sep in ["", " ", "a"]:
        compare_with_keys(keys, sep)
        compare_with_keys(reversed(keys), sep)

        for _ in range(1000):
            random_keys = [random.sample(keys, 1)[0] for _ in range(50)]
            compare_with_keys(random_keys, sep)


def test_escape_code_decoder_ambiguous_cases():

    # Double-escapes should be treated as single, because
    # "Windows issues esc esc for a single press of escape key"
    check_decoder(' \x1b ', [" ", "escape", " "])
    check_decoder(' \x1b\x1b ', [" ", "escape", " "])
    check_decoder(' \x1b\x1b\x1b ', [" ", "escape", "escape",  " "])
    check_decoder(' \x1b\x1b\x1b\x1b ', [" ", "escape", "escape", " "])

    # This one is easily interpreted wrong
    check_decoder(' \x1b\x1b[[D', [" ", "escape", "f4"])

    # Could be [escape, shift+tab] or [escape, escape, tab] or [escape, tab]
    # This now eagerly interprets as shift+tab.
    check_decoder(' \x1b\x1b\x09', [" ", "escape", "shift+tab"])


def test_escape_code_decoder_partial():
    # As a whole
    decoder = EscapeCodeDecoder()
    result = decoder.decode("\x1b[A")
    assert result == ["up"]

    # Char by char
    decoder = EscapeCodeDecoder()
    result = decoder.decode("\x1b")
    assert result == []
    result = decoder.decode("[")
    assert result == []
    result = decoder.decode("A")
    assert result == ["up"]

    # In two pieces
    decoder = EscapeCodeDecoder()
    result = decoder.decode("\x1b[")
    assert result == []
    result = decoder.decode("A")
    assert result == ["up"]

    # In two pieces
    decoder = EscapeCodeDecoder()
    result = decoder.decode("\x1b")
    assert result == []
    result = decoder.decode("[A")
    assert result == ["up"]


    # Char by char, with flushes
    decoder = EscapeCodeDecoder()
    result = decoder.decode("\x1b", True)
    assert result == ['escape']
    result = decoder.decode("[", True)
    assert result == ['[']
    result = decoder.decode("A", True)
    assert result == ["A"]


def compare_with_keys(keys, sep=""):

    input = ""
    expected = []

    for key in keys:
        input += key
        expected.extend(KEY_MAP[key])
        input += sep
        for s in sep:
            expected.append(s)

    check_decoder(input, expected)


def check_decoder(input, expected):
    decoder = EscapeCodeDecoder()
    result = decoder.decode(input, flush=True)

    info = "decoded result differs from expectation:\n\n"
    info += "input: " + repr(input) + "\n\n"
    if result != expected:
        info += f"  {'RESULT':>12}  EXPECTED\n\n"
        for v1, v2 in zip(result, expected):
            info += "X "[v1 == v2] + f" {v1:>12}  {v2}\n"
        for v1 in result[len(expected):]:
            info += f"+ {v1:>12}  \n"
        for v2 in expected[len(result):]:
            info += f"- {'':>12}  {v2}\n"
    assert result == expected, info


if __name__ == "__main__":
    test_escape_code_decoder_partial()
    test_escape_code_decoder()
    test_escape_code_decoder_ambiguous_cases()

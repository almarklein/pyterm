from pyterm.prompt import AutocompHelper


def test_autocomp_helper():

    # --- A tiny list

    ah = AutocompHelper()
    ah.show([f"line{i}" for i in range(3)])

    lines = ah.get_lines()
    assert len(lines) == 7

    for i in range(3):
        assert "\x1b[0m█" in lines[i]
        assert f"line{i}" in lines[i]
    for i in range(3, 7):
        assert lines[i] == ""

    # --- A list that fits exactly

    ah = AutocompHelper()
    ah.show([f"line{i}" for i in range(7)])

    lines = ah.get_lines()
    assert len(lines) == 7

    for i in range(7):
        assert "\x1b[0m█" in lines[i]
        assert f"line{i}" in lines[i]

    ah.up()
    lines = ah.get_lines()

    for i in range(7):
        assert "\x1b[0m█" in lines[i]
        assert f"line{i}" in lines[i]

    # --- A list that is one item too long to fit

    ah = AutocompHelper()
    ah.show([f"line{i}" for i in range(8)])

    lines = ah.get_lines()
    assert len(lines) == 7

    for i in range(7):
        assert f"line{i}" in lines[i]
    for i in range(6):
        assert "\x1b[0m█" in lines[i]
    assert "\x1b[2m█" in lines[6]  # dimmed scroll bar char

    ah.up()
    lines = ah.get_lines()

    for i in range(7):
        assert f"line{i+1}" in lines[i]
    assert "\x1b[2m█" in lines[0]  # dimmed
    for i in range(1, 7):
        assert "\x1b[0m█" in lines[i]

    # --- A list that is way too long to fit

    ah = AutocompHelper()
    ah.show([f"line{i}" for i in range(100)])

    lines = ah.get_lines()
    assert len(lines) == 7

    for i in range(7):
        assert f"line{i}" in lines[i]
    assert "\x1b[0m█" in lines[0]
    for i in range(1, 7):
        assert "\x1b[2m█" in lines[i]  # dimmed

    ah.up()
    lines = ah.get_lines()

    for i in range(7):
        assert f"line{i+93}" in lines[i]
    for i in range(6):
        assert "\x1b[2m█" in lines[i]  # dimmed
    assert "\x1b[0m█" in lines[6]

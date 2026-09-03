from omakeyfig import lighting


def test_standard_light_buffer_layout():
    st = lighting.LightingState(effect="Steady", brightness=4, speed=3,
                                color="#ff0000", random=False, sleep=5)
    buf = lighting.build_lighting_report(st)
    assert len(buf) == 65
    assert bytes(buf[0:6]) == bytes((0x0A, 0x01, 0x01, 0x02, 0x29, 17))
    assert buf[7] == 3 and buf[8] == 4
    assert bytes(buf[9:12]) == bytes((0xFF, 0x00, 0x00))
    assert buf[12] == 0x00 and buf[13] == 5


def test_random_flag_skips_color():
    st = lighting.LightingState(effect="Breathing", random=True)
    buf = lighting.build_lighting_report(st)
    assert buf[5] == 18 and buf[12] == 0x01
    assert bytes(buf[9:12]) == bytes((0, 0, 0))

"""Regression: overlay can reach the full display bottom even over taskbar."""
from bss_booster.overlay_geometry import bottom_edge_y, clamp_overlay_position


def test_bottom_placement_includes_taskbar():
    # 1080px display, Windows work area typically stops around y=1032.
    assert bottom_edge_y(0, 1080, 19) == 1061
    assert clamp_overlay_position(200, 1061, 0, 0, 1920, 1080, 503, 19) == (200, 1061)


def test_clamps_only_beyond_full_screen():
    assert clamp_overlay_position(0, 1200, 0, 0, 1920, 1080, 503, 19) == (0, 1061)
    assert clamp_overlay_position(1700, 900, 0, 0, 1920, 1080, 503, 19) == (1417, 900)


def test_supports_offset_secondary_monitor():
    assert clamp_overlay_position(2100, 1020, 1920, 0, 1920, 1080, 503, 19) == (2100, 1020)
    assert bottom_edge_y(100, 900, 25) == 975

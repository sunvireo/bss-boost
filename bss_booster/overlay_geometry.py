"""Pure screen-placement rules for the transparent hotbar overlay.

Qt's availableGeometry() EXCLUDES the Windows taskbar. Use QScreen.geometry()
(the full display rectangle) with these helpers so players can move the AUTO
buttons right down to the physical bottom edge of their monitor.
"""


def clamp_overlay_position(x: int, y: int, left: int, top: int,
                           screen_width: int, screen_height: int,
                           overlay_width: int, overlay_height: int) -> tuple[int, int]:
    """Keep the overlay on a display while permitting the full taskbar region."""
    rightmost = left + max(0, screen_width - overlay_width)
    bottommost = top + max(0, screen_height - overlay_height)
    return (max(left, min(x, rightmost)), max(top, min(y, bottommost)))


def bottom_edge_y(top: int, screen_height: int, overlay_height: int) -> int:
    """Top-left Y of an overlay whose bottom touches the actual display edge."""
    return top + max(0, screen_height - overlay_height)

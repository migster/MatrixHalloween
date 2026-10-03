import math
import random
import time

import board
import displayio
import framebufferio
import rgbmatrix


WIDTH = 64
HEIGHT = 64
FACE_DURATION = 120
MIN_BLINK_DELAY = 5
MAX_BLINK_DELAY = 20
WINK_CHANCE = 0.25
GHOST_MIN_DELAY = 30
GHOST_MAX_DELAY = 90
GHOST_SPEED = 10

BACKGROUND_COLOR = 0
EYE_COLOR = 1
NOSE_COLOR = 2
MOUTH_COLOR = 3

GHOST_SPRITE = (
    "....GGGGG....",
    "..GGGGGGGGG..",
    ".GGGGGGGGGGG.",
    "GGGGGGGGGGGGG",
    "GGGXGGGGGXGGG",
    "GGGGGGGGGGGGG",
    "GGGGGGGGGGGGG",
    "GGGGGGGGGGGGG",
    "GGGG.GGG.GGGG",
    "GGG...G...GGG",
)
GHOST_WIDTH = len(GHOST_SPRITE[0])

FACE_STYLES = (
    ("Happy pumpkin", "happy"),
    ("Angry pumpkin", "angry"),
    ("Evil grin", "evil"),
    ("Surprised face", "surprised"),
    ("One-eyed wink", "wink"),
)


def point_in_triangle(px, py, point_a, point_b, point_c):
    def edge(point_1, point_2):
        return (
            (px - point_2[0]) * (point_1[1] - point_2[1])
            - (point_1[0] - point_2[0]) * (py - point_2[1])
        )

    edge_1 = edge(point_a, point_b)
    edge_2 = edge(point_b, point_c)
    edge_3 = edge(point_c, point_a)
    has_negative = edge_1 < 0 or edge_2 < 0 or edge_3 < 0
    has_positive = edge_1 > 0 or edge_2 > 0 or edge_3 > 0
    return not (has_negative and has_positive)


def fill_triangle(bitmap, point_a, point_b, point_c, color):
    min_x = max(0, min(point_a[0], point_b[0], point_c[0]))
    max_x = min(WIDTH - 1, max(point_a[0], point_b[0], point_c[0]))
    min_y = max(0, min(point_a[1], point_b[1], point_c[1]))
    max_y = min(HEIGHT - 1, max(point_a[1], point_b[1], point_c[1]))

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if point_in_triangle(x, y, point_a, point_b, point_c):
                bitmap[x, y] = color


def draw_line(bitmap, x_1, y_1, x_2, y_2, color, thickness=1):
    delta_x = abs(x_2 - x_1)
    step_x = 1 if x_1 < x_2 else -1
    delta_y = -abs(y_2 - y_1)
    step_y = 1 if y_1 < y_2 else -1
    error = delta_x + delta_y

    while True:
        for offset_y in range(-(thickness // 2), thickness - thickness // 2):
            for offset_x in range(-(thickness // 2), thickness - thickness // 2):
                x = x_1 + offset_x
                y = y_1 + offset_y
                if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                    bitmap[x, y] = color

        if x_1 == x_2 and y_1 == y_2:
            break

        doubled_error = 2 * error
        if doubled_error >= delta_y:
            error += delta_y
            x_1 += step_x
        if doubled_error <= delta_x:
            error += delta_x
            y_1 += step_y


def eye_points(side, style):
    if style == "angry":
        if side == "left":
            return ((6, 15), (29, 21), (17, 31))
        return ((58, 15), (35, 21), (47, 31))

    if style == "evil":
        if side == "left":
            return ((7, 17), (30, 20), (20, 28))
        return ((57, 17), (34, 20), (44, 28))

    if style == "surprised":
        if side == "left":
            return ((17, 12), (6, 29), (29, 29))
        return ((47, 12), (35, 29), (58, 29))

    if side == "left":
        return ((7, 17), (28, 20), (14, 31))
    return ((57, 17), (36, 20), (50, 31))


def draw_eye(bitmap, side, openness, style):
    center_y = 23
    closed_line = (9, 26) if side == "left" else (38, 55)

    if style == "wink" and side == "left":
        draw_line(
            bitmap,
            closed_line[0],
            center_y + 1,
            closed_line[1],
            center_y - 1,
            EYE_COLOR,
            2,
        )
        return

    if openness < 0.08:
        draw_line(
            bitmap,
            closed_line[0],
            center_y,
            closed_line[1],
            center_y,
            EYE_COLOR,
            2,
        )
        return

    points = eye_points(side, style)
    scaled_points = tuple(
        (x, int(center_y + (y - center_y) * openness)) for x, y in points
    )
    fill_triangle(bitmap, *scaled_points, EYE_COLOR)


def draw_nose(bitmap):
    fill_triangle(bitmap, (32, 31), (25, 42), (39, 42), NOSE_COLOR)


def draw_happy_mouth(bitmap, crooked=False):
    for x in range(10, 55):
        distance_from_center = x - 32
        y = 56 - (distance_from_center * distance_from_center * 10 // 484)
        if crooked:
            y -= (x - 10) // 15
        for thickness in range(3):
            bitmap[x, y - thickness] = MOUTH_COLOR

    draw_line(bitmap, 10, 45, 10, 49, MOUTH_COLOR, 2)
    draw_line(bitmap, 54, 45, 54, 49, MOUTH_COLOR, 2)


def draw_angry_mouth(bitmap):
    for x in range(11, 54):
        distance_from_center = x - 32
        y = 46 + (distance_from_center * distance_from_center * 9 // 441)
        for thickness in range(3):
            bitmap[x, y + thickness] = MOUTH_COLOR


def draw_evil_grin(bitmap):
    for x in range(11, 54):
        distance_from_center = abs(x - 32)
        top = 46 + distance_from_center // 10
        bottom = 57 - distance_from_center // 5
        for y in range(top, bottom + 1):
            bitmap[x, y] = MOUTH_COLOR

    for tooth_x in (19, 28, 37, 46):
        fill_triangle(
            bitmap,
            (tooth_x - 2, 47),
            (tooth_x + 2, 47),
            (tooth_x, 51),
            BACKGROUND_COLOR,
        )
        fill_triangle(
            bitmap,
            (tooth_x - 2, 56),
            (tooth_x + 2, 56),
            (tooth_x, 52),
            BACKGROUND_COLOR,
        )


def draw_surprised_mouth(bitmap):
    fill_triangle(bitmap, (32, 44), (22, 52), (32, 61), MOUTH_COLOR)
    fill_triangle(bitmap, (32, 44), (42, 52), (32, 61), MOUTH_COLOR)
    fill_triangle(bitmap, (32, 48), (27, 52), (32, 57), BACKGROUND_COLOR)
    fill_triangle(bitmap, (32, 48), (37, 52), (32, 57), BACKGROUND_COLOR)


def draw_face(bitmap, style, left_openness=1.0, right_openness=1.0):
    bitmap.fill(BACKGROUND_COLOR)
    draw_eye(bitmap, "left", left_openness, style)
    draw_eye(bitmap, "right", right_openness, style)
    draw_nose(bitmap)

    if style == "angry":
        draw_angry_mouth(bitmap)
    elif style == "evil":
        draw_evil_grin(bitmap)
    elif style == "surprised":
        draw_surprised_mouth(bitmap)
    else:
        draw_happy_mouth(bitmap, crooked=style == "wink")


def blink_openness(elapsed):
    close_time = 0.14
    hold_time = 0.08
    open_time = 0.18

    if elapsed < close_time:
        return 1.0 - elapsed / close_time
    if elapsed < close_time + hold_time:
        return 0.0
    if elapsed < close_time + hold_time + open_time:
        return (elapsed - close_time - hold_time) / open_time
    return 1.0


def next_blink_time(now):
    return now + random.uniform(MIN_BLINK_DELAY, MAX_BLINK_DELAY)


def next_ghost_time(now):
    return now + random.uniform(GHOST_MIN_DELAY, GHOST_MAX_DELAY)


def draw_ghost(bitmap, position_x, position_y):
    bitmap.fill(0)

    for sprite_y, row in enumerate(GHOST_SPRITE):
        screen_y = position_y + sprite_y
        if screen_y < 0 or screen_y >= HEIGHT:
            continue

        for sprite_x, pixel in enumerate(row):
            screen_x = position_x + sprite_x
            if pixel != "." and 0 <= screen_x < WIDTH:
                bitmap[screen_x, screen_y] = 2 if pixel == "X" else 1


displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=WIDTH,
    height=HEIGHT,
    bit_depth=3,
    doublebuffer=True,
    rgb_pins=(
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2,
    ),
    addr_pins=(
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD,
        board.MTX_ADDRE,
    ),
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)
face_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 4)
face_palette = displayio.Palette(4)
face_palette[BACKGROUND_COLOR] = 0x000000
face_palette[EYE_COLOR] = 0xFF8C00
face_palette[NOSE_COLOR] = 0xFF4800
face_palette[MOUTH_COLOR] = 0xD82A00

ghost_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 3)
ghost_palette = displayio.Palette(3)
ghost_palette[0] = 0x000000
ghost_palette[1] = 0xA8E8FF
ghost_palette[2] = 0x080018
ghost_palette.make_transparent(0)

root = displayio.Group()
root.append(displayio.TileGrid(face_bitmap, pixel_shader=face_palette))
root.append(displayio.TileGrid(ghost_bitmap, pixel_shader=ghost_palette))
display.root_group = root

current_face = 0
current_style = FACE_STYLES[current_face][1]
draw_face(face_bitmap, current_style)
display.refresh()

animation_kind = None
animation_started = 0
last_left_openness = 1.0
last_right_openness = 1.0
now = time.monotonic()
blink_at = next_blink_time(now)
change_face_at = now + FACE_DURATION
ghost_at = next_ghost_time(now)
ghost_active = False
ghost_started = 0
last_ghost_x = -100
last_ghost_y = -100

while True:
    now = time.monotonic()

    glow = (math.sin(now * 1.2) + 1.0) / 2.0
    brightness = int(70 + glow * 185)
    green = int(brightness * 0.42)
    face_palette[EYE_COLOR] = (brightness << 16) | (green << 8)

    if now >= change_face_at:
        current_face = (current_face + 1) % len(FACE_STYLES)
        current_style = FACE_STYLES[current_face][1]
        animation_kind = None
        last_left_openness = 1.0
        last_right_openness = 1.0
        draw_face(face_bitmap, current_style)
        blink_at = next_blink_time(now)
        change_face_at = now + FACE_DURATION

    left_openness = 1.0
    right_openness = 1.0

    if animation_kind is None and now >= blink_at:
        if random.random() < WINK_CHANCE:
            animation_kind = "left" if random.random() < 0.5 else "right"
        else:
            animation_kind = "both"
        animation_started = now

    if animation_kind is not None:
        elapsed = now - animation_started
        openness = blink_openness(elapsed)

        if animation_kind in ("both", "left"):
            left_openness = openness
        if animation_kind in ("both", "right"):
            right_openness = openness

        if elapsed >= 0.4:
            animation_kind = None
            left_openness = 1.0
            right_openness = 1.0
            blink_at = next_blink_time(now)

    if (
        abs(left_openness - last_left_openness) >= 0.03
        or abs(right_openness - last_right_openness) >= 0.03
    ):
        draw_face(face_bitmap, current_style, left_openness, right_openness)
        last_left_openness = left_openness
        last_right_openness = right_openness

    if not ghost_active and now >= ghost_at:
        ghost_active = True
        ghost_started = now

    if ghost_active:
        ghost_elapsed = now - ghost_started
        ghost_x = int(-GHOST_WIDTH + ghost_elapsed * GHOST_SPEED)
        ghost_y = 1 + int((math.sin(ghost_elapsed * 2.5) + 1.0))

        if ghost_x > WIDTH:
            ghost_active = False
            ghost_bitmap.fill(0)
            ghost_at = next_ghost_time(now)
            last_ghost_x = -100
            last_ghost_y = -100
        elif ghost_x != last_ghost_x or ghost_y != last_ghost_y:
            draw_ghost(ghost_bitmap, ghost_x, ghost_y)
            last_ghost_x = ghost_x
            last_ghost_y = ghost_y

    display.refresh()
    time.sleep(0.03)

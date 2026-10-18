from array import array
import math
import random
import time

import audiobusio
import board
import digitalio
import displayio
import framebufferio
import rgbmatrix
import synthio


WIDTH = 64
HEIGHT = 64
FACE_DURATION = 120
MIN_BLINK_DELAY = 5
MAX_BLINK_DELAY = 20
WINK_CHANCE = 0.25
GHOST_MIN_DELAY = 30
GHOST_MAX_DELAY = 90
GHOST_SPEED = 10
AUDIO_SAMPLE_RATE = 22050
GHOST_SOUND_ATTACK = 0.8
GHOST_SOUND_RELEASE = 1.2
GHOST_SOUND_VOLUME = 0.35
PIR_DEBUG = True
PIR_SOUND_COOLDOWN = 60
PIR_SOUND_VOLUME = 0.6
GHOST_UNMUTE_BEEP_VOLUME = 0.4
BUTTON_DEBOUNCE_SECONDS = 0.25

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


ghost_waveform = array("h")
for sample_index in range(256):
    phase = 2 * math.pi * sample_index / 256
    ghost_waveform.append(int(32767 * math.sin(phase)))

laugh_waveform = array("h")
for sample_index in range(256):
    phase = 2 * math.pi * sample_index / 256
    sample = (
        0.65 * math.sin(phase)
        + 0.25 * math.sin(phase * 2)
        + 0.1 * math.sin(phase * 3)
    )
    laugh_waveform.append(int(32767 * sample))

rise_waveform = array("h", (-32768, 32767))
fall_waveform = array("h", (32767, -32768))

ghost_envelope = synthio.Envelope(
    attack_time=GHOST_SOUND_ATTACK,
    decay_time=0.4,
    release_time=GHOST_SOUND_RELEASE,
    attack_level=GHOST_SOUND_VOLUME,
    sustain_level=GHOST_SOUND_VOLUME * 0.75,
)
ghost_bends = (
    synthio.LFO(
        ghost_waveform,
        rate=0.18,
        scale=2.2,
    ),
    synthio.LFO(
        ghost_waveform,
        rate=0.23,
        scale=1.6,
        phase_offset=0.35,
    ),
)
ghost_tremolos = (
    synthio.LFO(
        ghost_waveform,
        rate=1.3,
        scale=0.12,
        offset=0.82,
    ),
    synthio.LFO(
        ghost_waveform,
        rate=1.7,
        scale=0.1,
        offset=0.72,
        phase_offset=0.5,
    ),
)
ghost_notes = (
    synthio.Note(
        frequency=155,
        waveform=ghost_waveform,
        envelope=ghost_envelope,
        bend=ghost_bends[0],
        amplitude=ghost_tremolos[0],
    ),
    synthio.Note(
        frequency=232.5,
        waveform=ghost_waveform,
        envelope=ghost_envelope,
        bend=ghost_bends[1],
        amplitude=ghost_tremolos[1],
    ),
)

laugh_envelope = synthio.Envelope(
    attack_time=0.03,
    decay_time=0.05,
    release_time=0.1,
    attack_level=PIR_SOUND_VOLUME,
    sustain_level=PIR_SOUND_VOLUME * 0.7,
)
laugh_bend = synthio.LFO(
    ghost_waveform,
    rate=7.0,
    scale=0.35,
)
laugh_note = synthio.Note(
    frequency=220,
    waveform=laugh_waveform,
    envelope=laugh_envelope,
    bend=laugh_bend,
)

long_effect_envelope = synthio.Envelope(
    attack_time=0.12,
    decay_time=0.1,
    release_time=0.3,
    attack_level=PIR_SOUND_VOLUME,
    sustain_level=PIR_SOUND_VOLUME * 0.75,
)
short_effect_envelope = synthio.Envelope(
    attack_time=0.02,
    decay_time=0.03,
    release_time=0.1,
    attack_level=PIR_SOUND_VOLUME,
    sustain_level=PIR_SOUND_VOLUME * 0.65,
)
scream_bend = synthio.LFO(
    rise_waveform,
    rate=0.65,
    scale=6.0,
    once=True,
)
scream_note = synthio.Note(
    frequency=420,
    waveform=laugh_waveform,
    envelope=long_effect_envelope,
    bend=scream_bend,
)
howl_bend = synthio.LFO(
    ghost_waveform,
    rate=0.55,
    scale=2.8,
)
howl_note = synthio.Note(
    frequency=185,
    waveform=ghost_waveform,
    envelope=long_effect_envelope,
    bend=howl_bend,
)
caw_bend = synthio.LFO(
    fall_waveform,
    rate=3.0,
    scale=3.0,
    once=True,
)
caw_note = synthio.Note(
    frequency=310,
    waveform=laugh_waveform,
    envelope=short_effect_envelope,
    bend=caw_bend,
)
heartbeat_note = synthio.Note(
    frequency=140,
    waveform=ghost_waveform,
    envelope=short_effect_envelope,
)
creak_bend = synthio.LFO(
    fall_waveform,
    rate=0.7,
    scale=7.0,
    once=True,
)
creak_note = synthio.Note(
    frequency=300,
    waveform=laugh_waveform,
    envelope=long_effect_envelope,
    bend=creak_bend,
)

PIR_SOUND_PATTERNS = (
    (
        "spooky laugh",
        (
            (0.00, laugh_note, 235, 0.18, laugh_bend),
            (0.28, laugh_note, 205, 0.20, laugh_bend),
            (0.58, laugh_note, 225, 0.18, laugh_bend),
            (0.88, laugh_note, 190, 0.22, laugh_bend),
            (1.22, laugh_note, 210, 0.20, laugh_bend),
            (1.55, laugh_note, 170, 0.32, laugh_bend),
        ),
    ),
    ("scream", ((0.00, scream_note, 420, 1.6, scream_bend),)),
    ("wolf howl", ((0.00, howl_note, 185, 2.8, howl_bend),)),
    (
        "raven caw",
        (
            (0.00, caw_note, 330, 0.20, caw_bend),
            (0.30, caw_note, 260, 0.30, caw_bend),
        ),
    ),
    (
        "heartbeat",
        (
            (0.00, heartbeat_note, 145, 0.12, None),
            (0.22, heartbeat_note, 115, 0.16, None),
            (0.75, heartbeat_note, 145, 0.12, None),
            (0.97, heartbeat_note, 115, 0.16, None),
            (1.50, heartbeat_note, 145, 0.12, None),
            (1.72, heartbeat_note, 115, 0.16, None),
        ),
    ),
    ("creaking door", ((0.00, creak_note, 300, 1.6, creak_bend),)),
)

unmute_beep_envelope = synthio.Envelope(
    attack_time=0.01,
    decay_time=0.02,
    release_time=0.05,
    attack_level=GHOST_UNMUTE_BEEP_VOLUME,
    sustain_level=GHOST_UNMUTE_BEEP_VOLUME * 0.8,
)
unmute_beep_note = synthio.Note(
    frequency=880,
    waveform=ghost_waveform,
    envelope=unmute_beep_envelope,
)

audio = audiobusio.I2SOut(
    bit_clock=board.A1,
    word_select=board.A2,
    data=board.A3,
)
synth = synthio.Synthesizer(
    sample_rate=AUDIO_SAMPLE_RATE,
    channel_count=1,
)
audio.play(synth)


def start_ghost_sound():
    for oscillator in ghost_bends + ghost_tremolos:
        oscillator.retrigger()
    synth.press(ghost_notes)


def stop_ghost_sound():
    synth.release(ghost_notes)


def start_pir_sound(now):
    global ghost_sound_released
    global pir_sound_active
    global pir_sound_name
    global pir_sound_note_active
    global pir_sound_pattern
    global pir_sound_pattern_index
    global pir_sound_started

    if not ghost_sound_released:
        stop_ghost_sound()
        ghost_sound_released = True

    pattern_index = int(random.random() * len(PIR_SOUND_PATTERNS))
    pir_sound_name, pir_sound_pattern = PIR_SOUND_PATTERNS[pattern_index]
    pir_sound_active = True
    pir_sound_note_active = False
    pir_sound_pattern_index = 0
    pir_sound_started = now

    if PIR_DEBUG:
        print("PIR sound started:", pir_sound_name)


def update_pir_sound(now):
    global pir_sound_active
    global pir_sound_note
    global pir_sound_note_active
    global pir_sound_note_ends
    global pir_sound_pattern_index

    if not pir_sound_active:
        return

    if pir_sound_note_active and now >= pir_sound_note_ends:
        synth.release(pir_sound_note)
        pir_sound_note_active = False

    elapsed = now - pir_sound_started
    if (
        not pir_sound_note_active
        and pir_sound_pattern_index < len(pir_sound_pattern)
        and elapsed >= pir_sound_pattern[pir_sound_pattern_index][0]
    ):
        _, note, frequency, duration, bend = pir_sound_pattern[
            pir_sound_pattern_index
        ]
        note.frequency = frequency
        if bend is not None:
            bend.retrigger()
        synth.press(note)
        pir_sound_note = note
        pir_sound_note_active = True
        pir_sound_note_ends = now + duration
        pir_sound_pattern_index += 1

    if (
        pir_sound_pattern_index == len(pir_sound_pattern)
        and not pir_sound_note_active
    ):
        pir_sound_active = False
        if PIR_DEBUG:
            print("PIR sound finished:", pir_sound_name)


def start_unmute_beep(now):
    global unmute_beep_active
    global unmute_beep_ends

    if unmute_beep_active:
        synth.release(unmute_beep_note)

    synth.press(unmute_beep_note)
    unmute_beep_active = True
    unmute_beep_ends = now + 0.2


def update_unmute_beep(now):
    global unmute_beep_active

    if unmute_beep_active and now >= unmute_beep_ends:
        synth.release(unmute_beep_note)
        unmute_beep_active = False


pir = digitalio.DigitalInOut(board.A4)
pir.switch_to_input(pull=digitalio.Pull.DOWN)
last_pir_value = pir.value

down_button = digitalio.DigitalInOut(board.BUTTON_DOWN)
down_button.switch_to_input(pull=digitalio.Pull.UP)
last_down_button_value = down_button.value

if PIR_DEBUG:
    print("PIR debug enabled on A4")
    print("Initial PIR signal:", "HIGH" if last_pir_value else "LOW")


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
ghost_sound_released = True
last_ghost_x = -100
last_ghost_y = -100
ghost_crossing_duration = (WIDTH + GHOST_WIDTH + 1) / GHOST_SPEED
pir_sound_active = False
pir_sound_name = ""
pir_sound_note = laugh_note
pir_sound_note_active = False
pir_sound_note_ends = 0
pir_sound_pattern = ()
pir_sound_pattern_index = 0
pir_sound_started = 0
next_pir_sound_allowed_at = 0
ghost_sound_muted = False
unmute_beep_active = False
unmute_beep_ends = 0
next_button_press_at = 0

while True:
    now = time.monotonic()

    down_button_value = down_button.value
    if (
        not down_button_value
        and last_down_button_value
        and now >= next_button_press_at
    ):
        ghost_sound_muted = not ghost_sound_muted
        next_button_press_at = now + BUTTON_DEBOUNCE_SECONDS

        if ghost_sound_muted and not ghost_sound_released:
            stop_ghost_sound()
            ghost_sound_released = True

        if not ghost_sound_muted:
            start_unmute_beep(now)
        print("Ghost sound muted" if ghost_sound_muted else "Ghost sound enabled")
    last_down_button_value = down_button_value

    pir_value = pir.value
    if pir_value != last_pir_value:
        if PIR_DEBUG:
            if pir_value:
                print("PIR motion signal received on A4: HIGH")
            else:
                print("PIR signal cleared on A4: LOW")
        if pir_value:
            if now >= next_pir_sound_allowed_at:
                start_pir_sound(now)
                next_pir_sound_allowed_at = now + PIR_SOUND_COOLDOWN
            elif PIR_DEBUG:
                cooldown_remaining = int(
                    next_pir_sound_allowed_at - now + 0.999
                )
                print(
                    "PIR sound suppressed; cooldown remaining:",
                    cooldown_remaining,
                    "seconds",
                )
        last_pir_value = pir_value

    update_pir_sound(now)
    update_unmute_beep(now)

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
        if pir_sound_active or ghost_sound_muted:
            ghost_sound_released = True
        else:
            ghost_sound_released = False
            start_ghost_sound()

    if ghost_active:
        ghost_elapsed = now - ghost_started
        ghost_x = int(-GHOST_WIDTH + ghost_elapsed * GHOST_SPEED)
        ghost_y = 1 + int((math.sin(ghost_elapsed * 2.5) + 1.0))

        if (
            not ghost_sound_released
            and ghost_elapsed >= ghost_crossing_duration - GHOST_SOUND_RELEASE
        ):
            stop_ghost_sound()
            ghost_sound_released = True

        if ghost_x > WIDTH:
            if not ghost_sound_released:
                stop_ghost_sound()
                ghost_sound_released = True
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

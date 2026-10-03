import time

import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
from adafruit_display_text import label


WIDTH = 64
HEIGHT = 64


displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=WIDTH,
    height=HEIGHT,
    bit_depth=3,
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

display = framebufferio.FramebufferDisplay(matrix)
root = displayio.Group()

background_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
background_palette = displayio.Palette(1)
background_palette[0] = 0x000008
root.append(displayio.TileGrid(background_bitmap, pixel_shader=background_palette))

border_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 2)
border_palette = displayio.Palette(2)
border_palette[0] = 0x000000
border_palette[1] = 0x002040
border_palette.make_transparent(0)

for x in range(WIDTH):
    border_bitmap[x, 0] = 1
    border_bitmap[x, HEIGHT - 1] = 1

for y in range(HEIGHT):
    border_bitmap[0, y] = 1
    border_bitmap[WIDTH - 1, y] = 1

root.append(displayio.TileGrid(border_bitmap, pixel_shader=border_palette))

hello = label.Label(
    terminalio.FONT,
    text="HELLO",
    color=0x00FFFF,
    anchor_point=(0.5, 0.5),
    anchored_position=(WIDTH // 2, 23),
)
world = label.Label(
    terminalio.FONT,
    text="WORLD!",
    color=0xFF00FF,
    anchor_point=(0.5, 0.5),
    anchored_position=(WIDTH // 2, 41),
)
root.append(hello)
root.append(world)

display.root_group = root

colors = (0x00FFFF, 0xFF00FF, 0xFFFF00)
color_index = 0

while True:
    hello.color = colors[color_index]
    world.color = colors[(color_index + 1) % len(colors)]
    color_index = (color_index + 1) % len(colors)
    time.sleep(1)

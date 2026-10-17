# MatrixHalloween

An animated jack-o'-lantern face for:

- Adafruit Matrix Portal S3, PID 5778
- One 64x64 RGB LED Matrix, 2.5 mm pitch, 1/32 scan, PID 3649
- One speaker driven by an NS4168 I2S amplifier
- One HC-SR501 PIR motion sensor

## Phase 4

The current `code.py` draws five smooth geometric faces:

1. Happy pumpkin
2. Angry pumpkin
3. Evil grin
4. Surprised face
5. One-eyed wink

The display advances to the next face every two minutes. Each face retains the
Phase 1 animation:

- slowly pulsing orange eyes;
- a random blink every 5 to 20 seconds; and
- an occasional left or right wink; and
- a small, gently bobbing ghost that crosses the top of the display.

As the ghost crosses the display, the NS4168 plays a synthesized, two-voice
ghost wail. Slow pitch bends create the rising and falling voice, faster
amplitude modulation adds a tremolo, and an envelope fades the sound in and
out. The sound is generated entirely by CircuitPython's built-in `synthio`
module, so no WAV file is required.

When the PIR sensor detects motion on A4, the speaker plays a synthesized
spooky laugh. The laugh takes priority over the ghost wail and has an
independent volume setting. A configurable cooldown prevents repeated motion
from playing the laugh too frequently.

The faces use the large triangular eyes and triangular nose from Phase 1.
Expression-specific eye angles and mouth shapes distinguish each face without
the blocky appearance of scaled pixel art. No external bitmap files or
additional libraries are required.

Display updates use manual refresh and RGB matrix double buffering. Each face
is drawn completely before it is presented, preventing partially drawn frames
from appearing during blinks and expression changes.

## Project files

```text
MatrixHalloween/
├── code.py                 Phase 4 animated face, sound, and motion trigger
├── hello-world-test.py     Archived hardware test
└── README.md
```

The Phase 4 program only uses modules built into CircuitPython. It does not
require anything in `CIRCUITPY/lib`.

The archived hardware test uses `adafruit_display_text`. To run that test,
install `adafruit_display_text` from the matching
[CircuitPython Library Bundle](https://circuitpython.org/libraries), copy
`hello-world-test.py` to `CIRCUITPY`, and rename it to `code.py`.

## Install

1. Install the latest stable CircuitPython release from the
   [MatrixPortal S3 download page](https://circuitpython.org/board/adafruit_matrixportal_s3/).
2. Disconnect USB power before attaching or removing the matrix.
3. Connect the MatrixPortal S3 to the matrix's input HUB75 connector.
4. Confirm that the red panel power lead is connected to `+5V` and black is
   connected to `GND`.
5. Bridge the MatrixPortal S3 **Address E** solder jumper to the pad marked
   **8**. The 64x64 1/32-scan panel needs this fifth row-address line.
6. Connect the NS4168 amplifier to the MatrixPortal S3:

   | NS4168 | MatrixPortal S3 |
   | ------ | --------------- |
   | BCLK   | A1              |
   | LRC    | A2              |
   | DIN    | A3              |

   Connect the amplifier and speaker power and ground according to the
   amplifier board's requirements, with a common ground shared by the
   MatrixPortal S3 and amplifier.
7. Connect the HC-SR501 PIR sensor to the MatrixPortal S3:

   | HC-SR501 | MatrixPortal S3 |
   | -------- | --------------- |
   | VCC      | +5V             |
   | OUT      | A4              |
   | GND      | GND             |

   Check the labels on the specific sensor before connecting it because some
   compatible modules arrange these three pins differently.
8. Copy this project's `code.py` to the root of the `CIRCUITPY` drive,
   replacing the existing file. CircuitPython reloads it automatically.

For this single-panel project, use the MatrixPortal S3's documented USB-C
power path rather than adding a separate panel power supply.

## Adjust the animation

The main settings are near the top of `code.py`:

```python
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
PIR_LAUGH_COOLDOWN = 60
PIR_LAUGH_VOLUME = 0.4
```

- `FACE_DURATION` controls the number of seconds each face remains visible.
  Set it to `10` temporarily to preview all five faces quickly.
- Blink delays are measured in seconds.
- `WINK_CHANCE` is the probability that a scheduled blink becomes a wink.
  Use `0.0` for no winks or `1.0` for only winks.
- Ghost delays and speed are measured in seconds and pixels per second. The
  next ghost appears 30 to 90 seconds after the previous ghost leaves.
- `GHOST_SOUND_ATTACK` and `GHOST_SOUND_RELEASE` control the fade-in and
  fade-out in seconds. `GHOST_SOUND_VOLUME` controls the peak synthesizer
  level; keep it between `0.0` and `1.0` and start low when testing a new
  speaker.
- `PIR_DEBUG` prints the initial A4 input state and every subsequent HIGH or
  LOW transition to the CircuitPython serial console. Set it to `False` after
  confirming the PIR wiring and signal.
- `PIR_LAUGH_COOLDOWN` is the minimum number of seconds between laughs.
  Additional motion triggers during this interval are ignored.
- `PIR_LAUGH_VOLUME` controls the laugh independently from the ghost wail.
  Keep it between `0.0` and `1.0` and start low to avoid distortion.
- Change `bit_depth=3` only if you need a different balance between color
  smoothness and matrix refresh performance.

## Face styles

The `FACE_STYLES` collection controls the display order. Drawing functions
define the expression geometry:

- Happy uses the original triangular eyes and curved smile.
- Angry tilts the eyes inward and uses a frown.
- Evil uses narrowed triangular eyes and a wide, toothed grin.
- Surprised uses tall triangular eyes and an open mouth.
- One-eyed wink uses one closed eye and a crooked smile.

## Troubleshooting

### Rows repeat or only half of the face appears

Confirm that the Address E jumper is bridged to **8** and that
`board.MTX_ADDRE` remains in `addr_pins`.

### The display is blank

- Confirm the panel is connected to its input connector, not its output.
- Confirm red is connected to `+5V` and black to `GND`.
- Try another data-capable USB-C cable and an adequately rated 5 V supply.
- Open the CircuitPython serial console and check for an exception.

### The colors are incorrect

This panel normally uses standard RGB order. Verify the panel PID and wiring
before changing the six `rgb_pins` entries in `code.py`.

### The panel flashes or glitches

The program disables automatic refresh and presents only completed frames. If
glitches remain after installing the latest `code.py`, check the USB-C cable
and power supply. A glitch that becomes more frequent when more LEDs are lit
usually indicates a power-delivery issue rather than an animation issue.

### The ghost is silent

- Confirm the amplifier wiring: BCLK to A1, LRC to A2, and DIN to A3.
- Confirm the amplifier and MatrixPortal S3 share a common ground.
- Verify that the amplifier is powered correctly and that any shutdown or
  enable pin on the amplifier board is asserted.
- Open the CircuitPython serial console and check for an exception indicating
  that `audiobusio` or `synthio` is unavailable in the installed build.

### The ghost sound is distorted or too loud

Lower `GHOST_SOUND_VOLUME` and restart CircuitPython. Also verify that the
speaker impedance and amplifier supply voltage are suitable for the NS4168
board. Avoid testing at maximum volume.

### The PIR sensor does not respond

With `PIR_DEBUG = True`, open the CircuitPython serial console and restart the
board. It should first report that PIR debugging is enabled and show the
initial A4 state. After the HC-SR501's 30-60 second warm-up period, motion
should produce a `HIGH` message and the signal returning idle should produce a
`LOW` message.

A valid motion trigger also prints `PIR spooky laugh started`. During the
60-second default cooldown, a new HIGH transition instead reports how many
seconds remain before another laugh is allowed.

If no transitions appear, verify that the HC-SR501 output is connected to A4,
that its ground is shared with the MatrixPortal S3, and that it is powered
from 5 V. Also confirm the pin order printed on the specific sensor module,
because some HC-SR501-compatible boards arrange the pins differently.

## References

- [Adafruit MatrixPortal S3 guide](https://learn.adafruit.com/adafruit-matrixportal-s3)
- [MatrixPortal S3 hardware preparation](https://learn.adafruit.com/adafruit-matrixportal-s3/prep-the-matrixportal)
- [RGB LED matrices with CircuitPython](https://learn.adafruit.com/rgb-led-matrices-matrix-panels-with-circuitpython)
- [CircuitPython `audiobusio` documentation](https://docs.circuitpython.org/en/latest/shared-bindings/audiobusio/)
- [CircuitPython `synthio` documentation](https://docs.circuitpython.org/en/latest/shared-bindings/synthio/)

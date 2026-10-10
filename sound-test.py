import time
import board
import audiobusio
import synthio

# NS4168 connections:
# BCL -> A1
# LRC -> A2
# DIN -> A3

audio = audiobusio.I2SOut(
    bit_clock=board.A1,
    word_select=board.A2,
    data=board.A3
)

synth = synthio.Synthesizer(
    sample_rate=22050,
    channel_count=1
)

audio.play(synth)

test_note = synthio.Note(440)

print("Audio test started")
print("One-second beep every five seconds")

while True:
    print("Beep")
    synth.press(test_note)
    time.sleep(1.0)

    synth.release(test_note)
    time.sleep(4.0)
#!/usr/bin/env python3
"""
Unifont Test - 64x36 cells with fancy Unicode characters
"""

import pygame
import pyunicodegame


def main():
    root = pyunicodegame.init(
        "Unifont Test 64x18",
        width=64,
        height=18,
        font_name="unifont",
        bg=(10, 10, 20, 255)
    )

    def render():
        # Title
        root.put_string(2, 0, "UNIFONT 64×18", (255, 255, 255))

        # Row 1: Sextants & Wedges
        sextants = ''.join(chr(0x1FB00 + i) for i in range(24))
        wedges = ''.join(chr(0x1FB3C + i) for i in range(16))
        root.put_string(1, 2, sextants, (100, 200, 255))
        root.put_string(26, 2, wedges, (100, 255, 200))

        # Row 2: Octants
        octants = ''.join(chr(0x1CC00 + i) for i in range(40))
        root.put_string(1, 3, octants, (255, 200, 100))

        # Row 3: Blocks & Shading
        root.put_string(1, 4, "▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏░▒▓█▖▗▘▙▚▛▜▝▞▟", (255, 150, 150))

        # Row 4: Box drawing
        root.put_string(1, 5, "┌─┬─┐├─┼─┤└─┴─┘╔═╦═╗╠═╬═╣╚═╩═╝", (200, 200, 255))

        # Row 5: Arabic
        root.put_string(1, 6, "ابتثجحخدذرزسشصضطظعغفقكلمنهوي", (150, 255, 150))

        # Row 6: Devanagari
        root.put_string(1, 7, "कखगघङचछजझञटठडढणतथदधनपफबभम", (255, 150, 200))

        # Row 7: Bengali & Tamil
        root.put_string(1, 8, "অআইঈউঊএঐওঔকখগঘ", (255, 180, 150))
        root.put_string(18, 8, "அஆஇஈஉஊஎஏஐஒஓஔக", (150, 200, 255))

        # Row 8: Georgian & Tibetan
        root.put_string(1, 9, "აბგდევზთიკლმნოპჟრ", (200, 255, 200))
        root.put_string(20, 9, "ཀཁགངཅཆཇཉཏཐདནཔཕབམ", (255, 255, 150))

        # Row 9: Braille
        braille = ''.join(chr(0x2800 + i) for i in range(48))
        root.put_string(1, 10, braille, (255, 255, 150))

        # Row 10: Emoji animals
        root.put_string(1, 11, "🐀🐁🐂🐃🐄🐅🐆🐇🐈🐕🐖🐘🐭🐮🐯🐰🐱🐴🐵🐶🐷🐸", (255, 200, 150))

        # Row 11: Chess, Cards, Music
        root.put_string(1, 12, "♔♕♖♗♘♙♚♛♜♝♞♟♠♡♢♣♤♥♦♧♩♪♫♬", (200, 255, 200))

        # Row 12: Stars & Shapes
        root.put_string(1, 13, "★☆✦✧✩✪✫✬●○◐◑◒◓◔◕■□▢▣▤▥▦▧▨▩", (255, 255, 180))

        # Row 13: Triangles & Arrows
        root.put_string(1, 14, "▲△▴▵▶▷▸▹►▻◀◁◂◃◄◅←↑→↓↔↕↖↗↘↙", (180, 220, 255))

        # Row 14: Weather & Zodiac
        root.put_string(1, 15, "☀☁☂☃☄♈♉♊♋♌♍♎♏♐♑♒♓◆◇◈◊⬥⬦", (255, 220, 180))

        # Footer
        root.put_string(2, 17, "Q to quit", (80, 80, 100))

    def on_key(key):
        if key == pygame.K_q:
            pyunicodegame.quit()

    pyunicodegame.run(render=render, on_key=on_key)


if __name__ == "__main__":
    main()

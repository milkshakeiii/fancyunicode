#!/usr/bin/env python3
"""
Cursive/Connecting Scripts Demo
Shows various scripts with connecting letters from around the world
"""

import pygame
import pyunicodegame


def main():
    root = pyunicodegame.init("Cursive Scripts", width=80, height=40, bg=(15, 15, 25, 255))

    scripts = [
        ("ARABIC", "ابتثجحخدذرزسشصضطظعغفقكلمنهوي", (255, 200, 100)),
        ("ARABIC+TATWEEL", "ـبـتـثـجـحـخـسـشـصـضـطـظـعـغـفـقـكـلـمـنـهـيـ", (255, 180, 80)),
        ("SYRIAC", "ܐܒܓܕܗܘܙܚܛܝܟܠܡܢܣܥܦܨܩܪܫܬ", (200, 150, 255)),
        ("DEVANAGARI", "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह", (100, 255, 200)),
        ("DEVANAGARI vowels", "अआइईउऊएऐओऔ", (80, 220, 180)),
        ("BENGALI", "অআইঈউঊএঐওঔকখগঘঙচছজঝঞটঠডঢণতথদধনপফবভম", (255, 150, 150)),
        ("TAMIL", "அஆஇஈஉஊஎஏஐஒஓஔகஙசஞடணதநபமயரலவழளறன", (150, 200, 255)),
        ("TIBETAN", "ཀཁགངཅཆཇཉཏཐདནཔཕབམཙཚཛཝཞཟའཡརལཤསཧཨ", (255, 255, 150)),
        ("GEORGIAN", "აბგდევზთიკლმნოპჟრსტუფქღყშჩცძწჭხჯჰ", (200, 255, 200)),
        ("THAI", "กขคงจฉชซญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหอฮ", (255, 180, 220)),
        ("HEBREW", "אבגדהוזחטיכלמנסעפצקרשת", (180, 220, 255)),
    ]

    scroll_y = 0
    max_scroll = max(0, len(scripts) * 3 - 30)

    def render():
        title_color = (100, 100, 120)
        root.put_string(2, 1, "CURSIVE & CONNECTING SCRIPTS", (200, 200, 220))
        root.put_string(2, 2, "=" * 40, title_color)

        y = 4 - scroll_y
        for name, chars, color in scripts:
            if 3 <= y < 38:
                # Script name
                root.put_string(2, y, name, title_color)
                # Characters
                # Wrap long lines
                x = 2
                char_y = y + 1
                for ch in chars:
                    if x >= 78:
                        x = 2
                        char_y += 1
                    if 3 <= char_y < 38:
                        root.put(x, char_y, ch, color)
                    x += 1
            y += 3

        # Instructions
        root.put_string(2, 39, "UP/DOWN to scroll, Q to quit", (80, 80, 100))

    def on_key(key):
        nonlocal scroll_y
        if key == pygame.K_q:
            pyunicodegame.quit()
        elif key == pygame.K_UP:
            scroll_y = max(0, scroll_y - 1)
        elif key == pygame.K_DOWN:
            scroll_y = min(max_scroll, scroll_y + 1)

    pyunicodegame.run(render=render, on_key=on_key)


if __name__ == "__main__":
    main()

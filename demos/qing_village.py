#!/usr/bin/env python3
"""
清朝小村 - Qing Dynasty Village
Unicode art with Chinese characters on gates
"""

import pygame
import pyunicodegame


def main():
    root = pyunicodegame.init("清朝小村", width=80, height=30, bg=(15, 20, 35, 255))

    def render():
        # 夜空星星
        stars = [(5, 2), (15, 1), (25, 3), (40, 2), (55, 1), (70, 3), (35, 4), (60, 2)]
        for sx, sy in stars:
            root.put(sx, sy, "·", (100, 100, 140))

        # 月亮
        root.put(65, 3, "☽", (200, 200, 180))

        # 远山
        mountain = "▁▂▃▄▅▆▇█▇▆▅▄▃▂▁"
        for i, ch in enumerate(mountain):
            root.put(10 + i, 8, ch, (30, 40, 50))
            root.put(45 + i, 9, ch, (25, 35, 45))

        # 地面
        for x in range(80):
            root.put(x, 25, "▀", (40, 35, 30))

        # ═══════════════════════════════════
        # 左边的房子 - 茶馆
        # ═══════════════════════════════════
        house_x, house_y = 5, 15

        # 屋顶
        roof_color = (80, 60, 50)
        root.put_string(house_x, house_y, "▄▄▄▄▄▄▄▄▄▄▄▄", roof_color)
        root.put_string(house_x-1, house_y+1, "▀", roof_color)
        root.put_string(house_x, house_y+1, "██████████████", roof_color)
        root.put_string(house_x+13, house_y+1, "▀", roof_color)

        # 墙壁
        wall_color = (60, 55, 50)
        for row in range(2, 8):
            root.put(house_x, house_y + row, "│", wall_color)
            root.put(house_x + 13, house_y + row, "│", wall_color)

        # 门框和门
        door_frame = (70, 50, 40)
        root.put(house_x + 5, house_y + 3, "┌", door_frame)
        root.put(house_x + 6, house_y + 3, "──", door_frame)
        root.put(house_x + 8, house_y + 3, "┐", door_frame)
        for row in range(4, 8):
            root.put(house_x + 5, house_y + row, "│", door_frame)
            root.put(house_x + 8, house_y + row, "│", door_frame)

        # 牌匾 - 茶
        root.put(house_x + 6, house_y + 2, "茶", (200, 180, 100))
        root.put(house_x + 7, house_y + 2, "馆", (200, 180, 100))

        # 灯笼
        lantern_color = (255, 100, 50)
        root.put(house_x + 2, house_y + 3, "◯", lantern_color)
        root.put(house_x + 11, house_y + 3, "◯", lantern_color)

        # ═══════════════════════════════════
        # 中间的大门 - 村口牌坊
        # ═══════════════════════════════════
        gate_x, gate_y = 32, 13

        # 牌坊顶
        gate_color = (90, 70, 60)
        root.put_string(gate_x, gate_y, "▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄", gate_color)
        root.put_string(gate_x-1, gate_y+1, "█", gate_color)
        root.put_string(gate_x, gate_y+1, "████████████████", gate_color)
        root.put_string(gate_x+16, gate_y+1, "█", gate_color)

        # 牌匾文字
        text_color = (255, 220, 150)
        root.put_string(gate_x + 4, gate_y + 1, "太平盛世", text_color)

        # 柱子
        pillar_color = (100, 60, 50)
        for row in range(2, 12):
            root.put(gate_x + 1, gate_y + row, "║", pillar_color)
            root.put(gate_x + 14, gate_y + row, "║", pillar_color)

        # 对联
        couplet_color = (200, 50, 50)
        left_couplet = "风调雨顺"
        right_couplet = "国泰民安"
        for i, ch in enumerate(left_couplet):
            root.put(gate_x, gate_y + 3 + i, ch, couplet_color)
        for i, ch in enumerate(right_couplet):
            root.put(gate_x + 15, gate_y + 3 + i, ch, couplet_color)

        # ═══════════════════════════════════
        # 右边的房子 - 客栈
        # ═══════════════════════════════════
        house2_x, house2_y = 58, 14

        # 屋顶
        root.put_string(house2_x, house2_y, "▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄", roof_color)
        root.put_string(house2_x-1, house2_y+1, "▀", roof_color)
        root.put_string(house2_x, house2_y+1, "██████████████████", roof_color)
        root.put_string(house2_x+17, house2_y+1, "▀", roof_color)

        # 墙壁
        for row in range(2, 10):
            root.put(house2_x, house2_y + row, "│", wall_color)
            root.put(house2_x + 17, house2_y + row, "│", wall_color)

        # 招牌 - 悦来客栈
        sign_color = (180, 150, 80)
        root.put(house2_x + 1, house2_y + 2, "┌", sign_color)
        root.put(house2_x + 2, house2_y + 2, "─", sign_color)
        root.put(house2_x + 3, house2_y + 2, "┐", sign_color)
        root.put(house2_x + 1, house2_y + 3, "│", sign_color)
        root.put(house2_x + 2, house2_y + 3, "悦", (255, 200, 100))
        root.put(house2_x + 3, house2_y + 3, "│", sign_color)
        root.put(house2_x + 1, house2_y + 4, "│", sign_color)
        root.put(house2_x + 2, house2_y + 4, "来", (255, 200, 100))
        root.put(house2_x + 3, house2_y + 4, "│", sign_color)
        root.put(house2_x + 1, house2_y + 5, "│", sign_color)
        root.put(house2_x + 2, house2_y + 5, "客", (255, 200, 100))
        root.put(house2_x + 3, house2_y + 5, "│", sign_color)
        root.put(house2_x + 1, house2_y + 6, "│", sign_color)
        root.put(house2_x + 2, house2_y + 6, "栈", (255, 200, 100))
        root.put(house2_x + 3, house2_y + 6, "│", sign_color)
        root.put(house2_x + 1, house2_y + 7, "└", sign_color)
        root.put(house2_x + 2, house2_y + 7, "─", sign_color)
        root.put(house2_x + 3, house2_y + 7, "┘", sign_color)

        # 门
        for row in range(5, 10):
            root.put(house2_x + 8, house2_y + row, "│", door_frame)
            root.put(house2_x + 11, house2_y + row, "│", door_frame)
        root.put(house2_x + 8, house2_y + 4, "┌", door_frame)
        root.put(house2_x + 9, house2_y + 4, "──", door_frame)
        root.put(house2_x + 11, house2_y + 4, "┐", door_frame)

        # 窗户
        window_color = (150, 140, 100)
        root.put(house2_x + 14, house2_y + 4, "田", window_color)
        root.put(house2_x + 14, house2_y + 6, "田", window_color)

        # 灯笼
        root.put(house2_x + 6, house2_y + 3, "◯", lantern_color)
        root.put(house2_x + 13, house2_y + 3, "◯", lantern_color)

        # 底部装饰 - 石板路
        path_color = (50, 45, 40)
        for x in range(25, 55):
            if x % 3 == 0:
                root.put(x, 24, "▪", path_color)

    def on_key(key):
        if key == pygame.K_q:
            pyunicodegame.quit()

    pyunicodegame.run(render=render, on_key=on_key)


if __name__ == "__main__":
    main()

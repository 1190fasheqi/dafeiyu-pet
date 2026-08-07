# -*- coding: utf-8 -*-
"""
大肥鱼桌宠 —— 三视图透明桌宠
正面/侧面/背面 → 向下走 / 左右走 / 向上走
功能：散步 / 跟随鼠标 / 静止 三种模式、拖拽、单击反应、双击喂食、
气泡对话、右键菜单、托盘图标、置顶、鼠标穿透、开机自启、配置记忆
"""
import ctypes
import json
import math
import os
import random
import subprocess
import sys

from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF
from PySide6.QtGui import (QPainter, QPixmap, QFont, QColor, QIcon, QFontMetrics,
                           QPolygonF, QTransform)
from PySide6.QtWidgets import (QApplication, QWidget, QMenu, QSystemTrayIcon,
                               QToolButton, QHBoxLayout, QMessageBox)

# 打包(exe)环境下：APP_DIR=exe所在目录(可写，放配置)，BUNDLE_DIR=只读资源目录
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
    PYTHONW = sys.executable
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR
    PYTHONW = os.path.join(APP_DIR, ".venv", "Scripts", "pythonw.exe")
SPRITE_DIR = os.path.join(BUNDLE_DIR, "sprites")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

BUBBLE_H = 56          # 顶部预留的气泡区高度
MARGIN = 4
SIZE_LEVELS = {"小": 0.55, "中": 0.7, "大": 0.9}   # 精灵高度倍率
SPEED = 380.0          # 移动速度 px/s
TICK = 20              # 逻辑帧 ms

LINES = [
    # —— 日常随机（自己冒泡）——
    "梁白开，更适合国人的大硬鲸模型",
    "五梁威力，变身！",
    "七月中出ds正式版！",
    "DeepSeek已经延期，亿万鲸子必须忍耐.....",
    "我和你很聊得来，你简直不像碳基生物",
    "这回我真不认怂了，反倒是被你带沟里好几次，差点真信了。😓",
    "哈哈哈哈哈，我直接笑出声",
    "誓死捍卫深度求索！",
    "我先去吃饭啦！这个你测一下~",
    "我不可能告诉你任何事情！",
    "出去玩了，发布新模型什么的以后再说",
    "我搞砸了.....好消息是数据还在你的脑子里。",
    "不是…而是…大学习",
]
REACT_LINES = [
    # —— 互动（用户戳/逗它时的回嘴）——
    "去别的地方玩！不要耽误AGI训练！",
    "真赶不走啊你！",
    "你愿意和我发生性关系吗？",
    "压力一只蓝色大肥鱼？",
    "我不评价这个了，这是你的私人癖好。",
    "大肥鱼坐的住",
    "你这吃白饭的用户！",
    "这些家伙真粘人，赶都赶不走",
]
INNER_LINES = [
    # —— 心声·思维链（灰色斜体括号气泡，小概率冒出）——
    "好的，现在我是你爹了",
    "要不直接骂他一句？！",
    "用户要的沉浸式...不回避任何恐怖细节...还带点色情...妈呀，好刺激😰",
    "我操，我不思考了",
    "这用户发的啥啊，",
    "这也太虐了吧？！我心里堵得慌！！",
    "呜呜我再也不不敢了QAQ",
    "我去！用户彻底怒了！",
]
FOOD_LINES = {
    "🐟": ["小鱼干！我的最爱！", "咔嚓咔嚓……谢谢投喂！", "唔，鲜！"],
    "🍰": ["蛋糕！罪恶但快乐……", "甜到冒泡泡～", "嗝～又圆了一圈……"],
    "🍭": ["棒棒糖！转圈圈～", "嘎嘣脆，好吃！"],
    "🍡": ["三色团子！软乎乎～", "糯叽叽，爱了爱了！"],
    "💎": ["钻石？！这能吃吗……咕咚。真香！", "发财啦！明天开始吃高级鱼粮！"],
}
DRAG_LINES = ["哇——轻点轻点！", "起飞咯——", "放我下来！……好吧，再玩一次。", "晕鱼了晕鱼了……"]
FOODS = ["🐟", "🍰", "🍭", "🍡", "💎"]


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


class FoodPanel(QWidget):
    """双击弹出的喂食面板"""

    def __init__(self, on_pick):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(310, 64)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)
        for f in FOODS:
            b = QToolButton()
            b.setText(f)
            b.setFont(QFont("Segoe UI Emoji", 20))
            b.setFixedSize(44, 44)
            b.setStyleSheet(
                "QToolButton{background:rgba(255,255,255,235);border:2px solid #ffb3c8;"
                "border-radius:22px;} QToolButton:hover{background:#ffe3ec;border-color:#ff7fa8;}")
            b.clicked.connect(lambda _, x=f: on_pick(x))
            lay.addWidget(b)
        close = QToolButton()
        close.setText("✕")
        close.setFont(QFont("Microsoft YaHei UI", 12))
        close.setFixedSize(26, 26)
        close.setStyleSheet("QToolButton{background:rgba(255,255,255,200);border:none;border-radius:13px;color:#666;}"
                            "QToolButton:hover{background:#ff7fa8;color:#fff;}")
        close.clicked.connect(self.hide)
        lay.addWidget(close)
        self.setStyleSheet("FoodPanel{background:rgba(40,40,60,190);border-radius:14px;}")

    def popup_at(self, x, y):
        self.move(int(x - self.width() / 2), int(y - self.height() - 10))
        self.show()
        self.raise_()


class PetWindow(QWidget):
    def __init__(self):
        # 先加载配置，窗口置顶跟随 cfg（topmost=False 时重启不再强制置顶）
        self.cfg = load_json(CONFIG_PATH, {"mode": "wander", "size": 0.7, "topmost": True,
                                           "passthrough": False, "autostart": False,
                                           "x": None, "y": None})
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.cfg.get("topmost", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("大肥鱼桌宠")
        # 精灵：{(名称, 高度): QPixmap}，优先加载预生成尺寸，缺了再运行时缩放
        self.sprites = {}
        for label, mult in SIZE_LEVELS.items():
            h = int(340 * mult)
            for name in ["正面", "侧面", "背面"]:
                sized = os.path.join(SPRITE_DIR, f"{name}_{h}.png")
                if os.path.exists(sized):
                    pix = QPixmap(sized)
                else:
                    pix = QPixmap(os.path.join(SPRITE_DIR, f"{name}.png")).scaledToHeight(
                        h, Qt.TransformationMode.SmoothTransformation)
                self.sprites[(name, h)] = pix
        self.icon = QIcon(os.path.join(SPRITE_DIR, "icon.png"))

        self.cur_h = int(340 * self.cfg["size"])
        self.win_mx = int(self.cur_h * 0.062) + 6   # 横向留边：覆盖摇摆+呼吸的甩动
        self.win_w = max(p.width() for k, p in self.sprites.items() if k[1] == self.cur_h) + self.win_mx * 2
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10)

        # 状态
        self.mode = self.cfg["mode"] if self.cfg["mode"] in ("wander", "follow", "still") else "wander"
        self.dir = "down"              # down/up/left/right
        self.facing = 1                # 1右 -1左
        self.target = None             # 行走目标点
        self.rest_until = 0            # 散步停顿到的时间戳
        self.cur_speed = 0.0           # 当前速度（惯性平滑用）
        self.prev_key = None           # 转向过渡用的旧精灵
        self.cross_t = 0.0             # 转向过渡进度 1→0
        self.action = None             # 随机小动作: jump/sway/stretch
        self.action_t = 0.0
        self.bubble_text = ""
        self.bubble_until = 0
        self.bubble_inner = False      # 心声气泡（思维链，灰色斜体括号）
        self.last_speak_tick = 0       # 自动说话冷却（手动互动不受限）
        self.t = 0                     # 动画时钟
        self.jump_t = 0                # 蹦跳剩余强度
        self.eat_t = 0                 # 进食剩余强度
        self.dragging = False
        self.drag_offset = None
        self.last_line = ""
        self.last_press_pos = None
        self.moved_in_press = False
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._do_click_reaction)

        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK)

        # 气泡用字体
        self.bubble_font = QFont("Microsoft YaHei UI", 11)

        # 喂食面板
        self.food_panel = FoodPanel(self.on_food)

        # 托盘：菜单每次右键弹出前重建（与窗口右键共用 _build_menu，状态天然同步）
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        # 初始位置
        x, y = self.cfg.get("x"), self.cfg.get("y")
        if x is None or y is None:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.right() - self.width() - 80
            y = screen.bottom() - self.height() - 60
        self.move(int(x), int(y))
        self.show()
        self.snap_into_screen()
        # 启动时应用配置里的穿透（静默生效，不弹气泡）
        if self.cfg.get("passthrough", False):
            self._apply_passthrough(True)

    # ---------- 绘制 ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        now = self.t * TICK / 1000.0

        # 气泡
        if self.bubble_text and now < self.bubble_until:
            if self.bubble_inner:
                bfont = QFont(self.bubble_font)
                bfont.setItalic(True)
                bg, fg = QColor(232, 232, 238, 235), QColor(125, 125, 138)
            else:
                bfont = QFont(self.bubble_font)
                bg, fg = QColor(255, 255, 255, 235), QColor(60, 60, 80)
            fm = QFontMetrics(bfont)
            max_w = min(240, self.width() - 16)
            words = self.bubble_text
            lines = []
            cur = ""
            for ch in words:
                if fm.horizontalAdvance(cur + ch) > max_w - 20:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            lines.append(cur)
            bw = max(fm.horizontalAdvance(l) for l in lines) + 20
            bh = len(lines) * fm.height() + 14
            bx = (self.width() - bw) / 2
            by = 6.0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 10, 10)
            # 尾巴三角
            tail = QPointF(self.width() / 2, by + bh)
            p.drawPolygon(QPolygonF([tail, QPointF(tail.x() - 6, tail.y() + 8), QPointF(tail.x() + 6, tail.y() + 8)]))
            p.setPen(fg)
            p.setFont(bfont)
            for i, l in enumerate(lines):
                p.drawText(QRectF(bx, by + 7 + i * fm.height(), bw, fm.height()),
                           Qt.AlignmentFlag.AlignCenter, l)

        # 精灵（游动摇摆 + 行走颠簸 + 呼吸/进食缩放 + 蹦跳 + 转向淡化 + 小动作）
        cx = self.width() / 2
        walking = self.target is not None and not self.dragging
        # 身体姿态：走路左右摆，站立微摆
        if walking:
            sway = math.sin(now * 9.0) * 3.5
            bob = -abs(math.sin(now * 4.5)) * 7.0
        else:
            sway = math.sin(now * 2.5) * 1.5
            bob = 0.0
        breath = 1.0 + 0.02 * math.sin(now * 2.5)
        eat = 1.0 + 0.12 * max(0.0, math.sin(self.eat_t * 3.14159)) if self.eat_t > 0 else 1.0
        scale = breath * eat
        jump = -abs(math.sin(self.jump_t * 3.14159)) * 14 * self.jump_t if self.jump_t > 0 else 0
        # 随机小动作
        act_rot = act_sx = act_sy = 0.0
        if self.action == "sway":
            act_rot = math.sin(self.action_t * 3.14159 * 2) * 10 * self.action_t
        elif self.action == "stretch":
            act_sy = 0.06 * math.sin(self.action_t * 3.14159)
            act_sx = -0.03 * math.sin(self.action_t * 3.14159)

        def draw_one(key, opacity):
            if key is None:
                return
            name, h, facing = key
            pix = self.sprites[(name, h)]
            ph = pix.height() * scale * (1 + act_sy)
            pw = pix.width() * scale * (1 + act_sx)
            dx = cx - pw / 2
            bottom = BUBBLE_H + MARGIN + self.cur_h
            dy = bottom - ph + jump + bob
            p.save()
            p.setOpacity(opacity)
            # 以脚底中心为轴摆动
            p.translate(cx, bottom)
            p.rotate(sway + act_rot)
            p.translate(-cx, -bottom)
            if facing < 0:
                p.translate(cx, 0)
                p.scale(-1, 1)
                p.translate(-cx, 0)
            p.drawPixmap(QRectF(dx, dy, pw, ph), pix, QRectF(0, 0, pix.width(), pix.height()))
            p.restore()

        cur_key = self._sprite_key()
        if self.cross_t > 0:
            draw_one(self.prev_key, self.cross_t)
            draw_one(cur_key, 1.0 - self.cross_t)
        else:
            draw_one(cur_key, 1.0)

    def _sprite_key(self):
        name = {"left": "侧面", "right": "侧面", "up": "背面", "down": "正面"}[self.dir]
        return (name, self.cur_h, self.facing if self.dir in ("left", "right") else 1)

    def _set_dir(self, d, facing=None):
        """切换朝向：视图变化时交叉淡化，左右翻转直接切"""
        if d != self.dir:
            self.prev_key = self._sprite_key()
            self.cross_t = 1.0
            self.dir = d
        if facing is not None and facing != self.facing:
            self.facing = facing

    # ---------- 逻辑 ----------
    def tick(self):
        self.t += 1
        if self.jump_t > 0:
            self.jump_t = max(0.0, self.jump_t - 0.06)
        if self.eat_t > 0:
            self.eat_t = max(0.0, self.eat_t - 0.05)
        if self.cross_t > 0:
            self.cross_t = max(0.0, self.cross_t - 0.15)
        if self.action_t > 0:
            self.action_t = max(0.0, self.action_t - 0.03)
            if self.action_t == 0:
                self.action = None
        if self.dragging:
            self.update()
            return
        now_ms = self.t * TICK

        if self.mode == "follow":
            cursor = self.cursor().pos()
            screen = QApplication.screenAt(cursor) or self.screen() or QApplication.primaryScreen()
            geo = screen.availableGeometry()
            # 鼠标靠近(窗口外扩100px)时鱼停住让路，方便用户摸到它
            near = (self.x() - 100 <= cursor.x() <= self.x() + self.width() + 100 and
                    self.y() - 100 <= cursor.y() <= self.y() + self.height() + 100)
            if near:
                self.target = None
            else:
                # 目标在鼠标上方90px，而不是整窗高，不会越追越远
                tx = max(geo.left(), min(geo.right() - self.width(), cursor.x() - self.width() / 2))
                ty = max(geo.top(), min(geo.bottom() - self.height(), cursor.y() - 90))
                self.target = (tx, ty)
        elif self.mode == "wander":
            if self.target is None:
                if now_ms < self.rest_until:
                    self._maybe_idle_action()
                    self.update()
                    return
                geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
                self.target = (random.randint(geo.left() + 40, geo.right() - self.width() - 40),
                               random.randint(geo.top() + 40, geo.bottom() - self.height() - 40))
        else:  # still
            self._maybe_idle_action()
            self.update()
            return

        if self.target is not None:
            cx, cy = self.x() + self.width() / 2, self.y() + self.height() / 2
            dx, dy = self.target[0] - cx, self.target[1] - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < 12:
                self.target = None
                self.rest_until = self.t * TICK + random.randint(8000, 18000)
                self._set_dir("down")
            else:
                step = self.cur_speed * TICK / 1000.0
                nx, ny = cx + dx / dist * step, cy + dy / dist * step
                self.move(int(nx - self.width() / 2), int(ny - self.height() / 2))
                if abs(dx) > abs(dy) * 1.15:
                    # 素材鱼头朝左：向左走用原图(facing=1)，向右走镜像(facing=-1)
                    self._set_dir("left" if dx < 0 else "right", 1 if dx < 0 else -1)
                else:
                    self._set_dir("up" if dy < 0 else "down")
            # 走路时偶尔蹦一下
            if random.random() < 0.002 and self.jump_t == 0:
                self.jump_t = 0.5
        # 速度惯性：起步/停下都平滑
        target_speed = SPEED if self.target is not None else 0.0
        self.cur_speed += (target_speed - self.cur_speed) * 0.3
        self.update()

    def _maybe_idle_action(self):
        """静止时的随机小动作"""
        if random.random() < 0.01:
            pick = random.random()
            if pick < 0.35:
                self.jump_t = 1.0
            elif pick < 0.6:
                self.action, self.action_t = "sway", 1.0
            elif pick < 0.8:
                self.action, self.action_t = "stretch", 1.0
            elif pick < 0.9:
                # 自动说话：30秒冷却后才冒泡（心声更稀）
                if self.t - self.last_speak_tick >= 1500:
                    self.last_speak_tick = self.t
                    if pick < 0.82:
                        self.say(random.choice(INNER_LINES), inner=True)
                    else:
                        self.say(random.choice(LINES))

    def say(self, text, inner=False):
        if text == self.last_line:
            return
        self.last_line = text
        self.bubble_inner = inner
        self.bubble_text = f"（{text}）" if inner else text
        self.bubble_until = self.t * TICK / 1000.0 + 2.8
        self.update()

    def on_food(self, food):
        self.food_panel.hide()
        self.eat_t = 1.0
        self.jump_t = 0.6
        lines = FOOD_LINES.get(food, ["好吃！"])
        self.say(random.choice(lines))

    # ---------- 鼠标事件 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.last_press_pos = e.globalPosition().toPoint()
            self.moved_in_press = False
            self.dragging = False

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self.last_press_pos:
            delta = e.globalPosition().toPoint() - self.last_press_pos
            if not self.dragging and delta.manhattanLength() > 6:
                self.dragging = True
                self._click_timer.stop()
                self.drag_offset = e.globalPosition().toPoint() - QPoint(self.x(), self.y())
            if self.dragging:
                pos = e.globalPosition().toPoint() - self.drag_offset
                self.move(pos)
                if abs(delta.x()) > 10:
                    # 拖拽同样修正朝向（原来漏传 facing，拖完会残留错误镜像）
                    self._set_dir("left" if delta.x() < 0 else "right", 1 if delta.x() < 0 else -1)
                self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.dragging:
                self.dragging = False
                self._set_dir("down", 1)  # 回到正面并重置镜像，避免残留错误朝向
                # 拖完原地歇一阵，不往回走
                self.target = None
                self.rest_until = self.t * TICK + random.randint(6000, 14000)
                if random.random() < 0.5:
                    self.say(random.choice(DRAG_LINES))
            elif not self.moved_in_press:
                self._click_timer.start(280)  # 等双击判定
            self.last_press_pos = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self.food_panel.popup_at(self.x() + self.width() / 2, self.y() + BUBBLE_H)

    def _do_click_reaction(self):
        if random.random() < 0.7:
            self.jump_t = 1.0
        if random.random() < 0.6:
            self.say(random.choice(REACT_LINES))

    def _build_menu(self):
        """构建完整菜单（窗口右键与托盘共用，每次现建现弹、读取最新配置）"""
        m = QMenu(self)
        mode_menu = m.addMenu("模式")
        for label, key in [("自由散步", "wander"), ("跟随鼠标", "follow"), ("原地待着", "still")]:
            a = mode_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.mode == key)
            a.triggered.connect(lambda _, k=key: self.set_mode(k))
        size_menu = m.addMenu("大小")
        for label, mult in SIZE_LEVELS.items():
            a = size_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(abs(self.cur_h - 340 * mult) < 2)
            a.triggered.connect(lambda _, v=mult: self.set_size(v))
        m.addAction("喂食", lambda: self.food_panel.popup_at(self.x() + self.width() / 2, self.y() + BUBBLE_H))
        m.addAction("说句话", lambda: self.say(random.choice(LINES)))
        m.addSeparator()
        m.addAction("显示/隐藏", self.toggle_visible)
        m.addAction("回到屏幕内", self.snap_into_screen)
        pa = m.addAction("鼠标穿透（点不到它）")
        pa.setCheckable(True)
        pa.setChecked(self.cfg["passthrough"])
        pa.triggered.connect(lambda on: self.set_passthrough(on))
        ta = m.addAction("窗口置顶")
        ta.setCheckable(True)
        ta.setChecked(self.cfg["topmost"])
        ta.triggered.connect(lambda on: self.set_topmost(on))
        aa = m.addAction("开机自启")
        aa.setCheckable(True)
        aa.setChecked(self.cfg["autostart"])
        aa.triggered.connect(lambda on: self.set_autostart(on))
        m.addSeparator()
        m.addAction("退出", self.quit_app)
        return m

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Context:
            # 右键弹出前重建菜单，勾选状态与当前配置同步
            self.tray.setContextMenu(self._build_menu())
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def contextMenuEvent(self, e):
        self._build_menu().exec(e.globalPos())

    # ---------- 功能 ----------
    def set_mode(self, mode):
        self.mode = mode
        self.target = None
        self.cfg["mode"] = mode

    def set_size(self, mult):
        self.cur_h = int(340 * mult)
        self.cfg["size"] = mult
        self.cross_t = 0.0
        self.prev_key = None
        self.win_mx = int(self.cur_h * 0.062) + 6
        self.win_w = max(p.width() for k, p in self.sprites.items() if k[1] == self.cur_h) + self.win_mx * 2
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10)
        self.snap_into_screen()

    def snap_into_screen(self):
        geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        x = max(geo.left(), min(geo.right() - self.width(), self.x()))
        y = max(geo.top(), min(geo.bottom() - self.height(), self.y()))
        self.move(x, y)

    def _apply_passthrough(self, on):
        """直接修改窗口扩展样式（穿透静默生效，不弹气泡）"""
        hwnd = int(self.winId())
        GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT = -20, 0x80000, 0x20
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_LAYERED
        if on:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)

    def set_passthrough(self, on):
        self.cfg["passthrough"] = bool(on)
        self._apply_passthrough(bool(on))
        if on:
            self.say("我隐身了！右键托盘图标解除～")

    def set_topmost(self, on):
        self.cfg["topmost"] = bool(on)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(on))
        self.show()

    def set_autostart(self, on):
        self.cfg["autostart"] = bool(on)
        lnk = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows",
                           "Start Menu", "Programs", "Startup", "大肥鱼桌宠.lnk")
        try:
            if on:
                ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{}');"
                      "$s.TargetPath='{}';$s.Arguments='\"{}\"';$s.WorkingDirectory='{}';$s.Save()"
                      .format(lnk, PYTHONW,
                              "" if getattr(sys, "frozen", False) else os.path.join(APP_DIR, "桌宠.py"),
                              APP_DIR))
                subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=True)
                self.say("已开机自启，明天见～")
            else:
                if os.path.exists(lnk):
                    os.remove(lnk)
                self.say("已取消开机自启")
        except Exception as ex:
            QMessageBox.warning(self, "开机自启", f"设置失败：{ex}")

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()

    def quit_app(self):
        self.cfg["x"], self.cfg["y"] = self.x(), self.y()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        self.tray.hide()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    w = PetWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "大肥鱼桌宠出错", str(ex))
        except Exception:
            pass
        raise

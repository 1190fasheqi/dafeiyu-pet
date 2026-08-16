# -*- coding: utf-8 -*-
"""桌宠.py 基础功能自动化测试（PySide6.QtTest 模拟真实鼠标/键盘事件）
运行：python test_pet.py
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
pet_mod = importlib.import_module("桌宠")

from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QPoint, QTimer

app = pet_mod.QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

pet = pet_mod.PetWindow()
pet.set_mode("still")          # 冻结散步，便于断言
pet.cfg["ds_api_key"] = "sk-test-fake"  # 主流程用假 Key，跳过设置框
pet.show()
QTest.qWait(400)

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))

CENTER = QPoint(pet.width() // 2, pet.height() // 2)

# ---------- 1. 单击：气泡 + 聊天按钮 + 暂停 ----------
QTest.mouseClick(pet, Qt.MouseButton.LeftButton, pos=CENTER)
QTest.qWait(500)
check("单击弹出气泡台词", bool(pet.bubble_text), pet.bubble_text)
check("单击弹出聊天按钮", pet.chat_button.isVisible())
check("按钮出现时鱼暂停", pet.chat_paused is True)

# ---------- 2. 点击按钮 → 聊天对话框打开、可聚焦、可输入 ----------
QTest.mouseClick(pet.chat_button, Qt.MouseButton.LeftButton)
QTest.qWait(350)
check("点击按钮打开聊天对话框", pet.chat_dialog.isVisible())
fw = app.focusWidget()
check("输入框获得焦点", fw is pet.chat_dialog.input, str(fw) if fw else "no focus widget")
QTest.keyClicks(pet.chat_dialog.input, "hello")
QTest.qWait(50)
check("对话框可输入文字", pet.chat_dialog.input.text() == "hello", pet.chat_dialog.input.text())
check("聊天期间鱼暂停", pet.chat_paused is True)

# ---------- 3. ESC 关闭对话框 → 恢复移动 ----------
QTest.keyClick(pet.chat_dialog, Qt.Key.Key_Escape)
QTest.qWait(150)
check("ESC 关闭对话框", not pet.chat_dialog.isVisible())
check("关闭后鱼恢复移动", pet.chat_paused is False)

# ---------- 4. 气泡与聊天按钮同步消失 ----------
QTest.mouseClick(pet, Qt.MouseButton.LeftButton, pos=CENTER)
QTest.qWait(500)
check("再次单击按钮出现", pet.chat_button.isVisible())
QTest.qWait(2000)   # 到 2.5s：气泡与按钮应同时还在
check("气泡到期前仍在显示", pet._bubble_geometry() is not None)
check("按钮与气泡同步仍显示", pet.chat_button.isVisible())
QTest.qWait(750)    # 到 ~3.3s：两者应同时消失
check("气泡与按钮同步消失", pet._bubble_geometry() is None and not pet.chat_button.isVisible())
check("同步消失后鱼恢复移动", pet.chat_paused is False)

# ---------- 5. 双击 → 喂食面板（且不残留聊天按钮） ----------
QTest.mouseDClick(pet, Qt.MouseButton.LeftButton, pos=CENTER)
QTest.qWait(250)
check("双击弹出喂食面板", pet.food_panel.isVisible())
check("双击后无聊天按钮残留", not pet.chat_button.isVisible())
food_btns = [b for b in pet.food_panel.findChildren(pet_mod.QToolButton) if b.text() in pet_mod.FOODS]
check("喂食面板有食物按钮", len(food_btns) == len(pet_mod.FOODS), str(len(food_btns)))
QTest.mouseClick(food_btns[0], Qt.MouseButton.LeftButton)
QTest.qWait(150)
check("选择食物后面板关闭", not pet.food_panel.isVisible())
check("喂食有回应台词", bool(pet.bubble_text), pet.bubble_text)
check("喂食后鱼恢复移动", pet.chat_paused is False)

# ---------- 6. 拖拽：位置变化 + 松手恢复 ----------
pos0 = pet.pos()
QTest.mousePress(pet, Qt.MouseButton.LeftButton, pos=CENTER)
QTest.mouseMove(pet, QPoint(CENTER.x() + 40, CENTER.y() + 40))
QTest.qWait(60)
QTest.mouseMove(pet, QPoint(CENTER.x() + 80, CENTER.y() + 80))
QTest.qWait(60)
QTest.mouseRelease(pet, Qt.MouseButton.LeftButton, pos=QPoint(CENTER.x() + 80, CENTER.y() + 80))
QTest.qWait(150)
check("拖拽后位置变化", pet.pos() != pos0, f"{pos0} -> {pet.pos()}")
check("拖拽松手后鱼恢复移动", pet.chat_paused is False)

# ---------- 7. 右键菜单结构 ----------
menu = pet._build_menu()
top = [a.text() for a in menu.actions()]
sub = [a.text() for sm in menu.findChildren(pet_mod.QMenu) for a in sm.actions()]
all_items = top + sub
for need in ("模式", "大小", "设置 Key", "查看天气", "显示/隐藏", "鼠标穿透（点不到它）",
             "窗口置顶", "开机自启", "退出", "自由散步", "跟随鼠标", "原地待着"):
    check(f"菜单含「{need}」", need in all_items)
menu.close()

# ---------- 8. 模式 / 大小切换 ----------
pet.set_mode("follow")
check("切换到跟随模式", pet.mode == "follow")
pet.set_mode("wander")
check("切换到散步模式", pet.mode == "wander")
pet.set_size(0.55)
check("切换小尺寸", pet.cur_h == int(340 * 0.55), str(pet.cur_h))
pet.set_size(0.7)
check("切回中尺寸", pet.cur_h == int(340 * 0.7), str(pet.cur_h))

# ---------- 9. 未设置 Key 时：自动弹出 Key 设置框，设置后打开聊天 ----------
pet.chat_dialog.hide()
pet.cfg["ds_api_key"] = ""
def auto_fill_key():
    dlg = app.activeModalWidget()
    if dlg is not None:
        le = dlg.findChild(pet_mod.QLineEdit)
        if le is not None:
            le.setText("sk-auto-123")
        dlg.accept()
QTimer.singleShot(400, auto_fill_key)
pet._show_chat_dialog()
QTest.qWait(400)
check("无 Key 时自动弹出设置框并填入", pet.cfg["ds_api_key"] == "sk-auto-123", pet.cfg["ds_api_key"])
check("设置 Key 后聊天对话框打开", pet.chat_dialog.isVisible())
check("聊天输入框可聚焦", app.focusWidget() is pet.chat_dialog.input)
QTest.keyClick(pet.chat_dialog, Qt.Key.Key_Escape)
QTest.qWait(120)

# ---------- 10. 对话框失去鼠标焦点 5 秒自动消失，桌宠恢复自动运行 ----------
pet.cfg["ds_api_key"] = "sk-test-fake"
pet._show_chat_dialog()
QTest.qWait(300)
check("聊天对话框打开", pet.chat_dialog.isVisible())
check("对话框打开时鱼暂停", pet.chat_paused is True)
# 模拟失去焦点（点击窗口外）
pet.chat_dialog.event(pet_mod.QEvent(pet_mod.QEvent.Type.WindowDeactivate))
QTest.qWait(5300)
check("失焦 5 秒后对话框自动消失", not pet.chat_dialog.isVisible())
check("对话框消失后鱼恢复自动运行", pet.chat_paused is False)

# 失焦后重新获得焦点 → 不消失
pet._show_chat_dialog()
QTest.qWait(200)
pet.chat_dialog.event(pet_mod.QEvent(pet_mod.QEvent.Type.WindowDeactivate))
QTest.qWait(800)
pet.chat_dialog.event(pet_mod.QEvent(pet_mod.QEvent.Type.WindowActivate))
QTest.qWait(5300)
check("重新获焦后对话框不消失", pet.chat_dialog.isVisible())
pet.chat_dialog.hide()
QTest.qWait(100)
check("手动关闭后鱼恢复自动运行", pet.chat_paused is False)

# ---------- 汇总 ----------
failed = [r for r in results if not r[1]]
print("\n" + "=" * 50)
print(f"总用例: {len(results)}  通过: {len(results) - len(failed)}  失败: {len(failed)}")
if failed:
    print("失败项:")
    for name, ok, detail in failed:
        print("  -", name, detail)
    sys.exit(1)
else:
    print("全部通过 ✅")
    sys.exit(0)

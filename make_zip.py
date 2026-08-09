# -*- coding: utf-8 -*-
"""打源码分享 zip（排除 venv/打包产物/配置）"""
import os
import zipfile

BASE = r"D:\图图\大肥鱼\桌宠程序"
OUT = r"D:\图图\大肥鱼\大肥鱼桌宠_源码.zip"

files = ["桌宠.py", "preprocess.py", "preprocess2.py", "启动桌宠.bat",
         "requirements.txt", "README.md", "LICENSE", "icon.ico", ".gitignore"]
for root, dirs, fs in os.walk(os.path.join(BASE, "sprites")):
    for f in fs:
        files.append(os.path.relpath(os.path.join(root, f), BASE).replace(os.sep, "/"))

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(os.path.join(BASE, f), f)

print("files:", len(files))
print("size:", os.path.getsize(OUT) // 1024, "KB")
for f in files:
    print(" ", f)

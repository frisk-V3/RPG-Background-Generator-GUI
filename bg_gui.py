#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
bg_gui.py
GUI付きのRPG背景生成ツール（単一ファイル完結）
依存: pillow, perlin-noise
このファイルはリポジトリのルートに置いてください。
"""

import os
import sys
import traceback
import logging
import random
import datetime
from typing import Tuple, Optional

# GUI
try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
except Exception as e:
    print("tkinter のインポートに失敗しました。GUI を使うには tkinter が必要です。")
    raise

# 画像処理
try:
    from PIL import Image
except Exception as e:
    # 明示的にエラーメッセージを出して終了する
    tk_available = 'tkinter' in sys.modules
    msg = (
        "Pillow (PIL) のインポートに失敗しました。\n"
        "このプログラムを実行するには Pillow が必要です。\n"
        "通常は 'pip install pillow' でインストールできます。"
    )
    if tk_available:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("依存ライブラリエラー", msg)
        root.destroy()
    else:
        print(msg)
    raise

# ノイズ生成
try:
    from perlin_noise import PerlinNoise
except Exception as e:
    tk_available = 'tkinter' in sys.modules
    msg = (
        "perlin-noise のインポートに失敗しました。\n"
        "このプログラムを実行するには perlin-noise が必要です。\n"
        "通常は 'pip install perlin-noise' でインストールできます。"
    )
    if tk_available:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("依存ライブラリエラー", msg)
        root.destroy()
    else:
        print(msg)
    raise

# ログ設定
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"bg_gui_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bg_gui")

# 定数と型
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
DEFAULT_OCTAVES = 4

def get_repo_name() -> str:
    """
    カレントディレクトリ名をリポジトリ名として返す。
    CIやzip展開などでカレントディレクトリが変わる可能性があるが、
    基本は os.getcwd() のベース名を使用する。
    """
    try:
        cwd = os.getcwd()
        repo_name = os.path.basename(os.path.abspath(cwd)) or "repository"
        logger.info("Repository name detected: %s", repo_name)
        return repo_name
    except Exception:
        logger.exception("リポジトリ名の取得に失敗しました。")
        return "repository"

def clamp_int(v: int, lo: int, hi: int) -> int:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v

def map_noise_to_color(value: float, palette: str) -> Tuple[int, int, int]:
    """
    - value: -1.0 〜 1.0 のノイズ値
    - palette: 'forest', 'desert', 'snow', 'night'
    ノイズ値をRGBにマッピングして返す。
    """
    # 正規化 0〜1
    nv = (value + 1.0) / 2.0
    nv = max(0.0, min(1.0, nv))

    if palette == "forest":
        # 緑系の深みを出す
        r = int(40 + nv * 80)      # 40〜120
        g = int(80 + nv * 140)     # 80〜220
        b = int(30 + nv * 80)      # 30〜110
    elif palette == "desert":
        # 砂漠っぽい黄土色
        r = int(180 + nv * 60)     # 180〜240
        g = int(140 + nv * 60)     # 140〜200
        b = int(80 + nv * 40)      # 80〜120
    elif palette == "snow":
        # 白〜薄青
        r = int(200 + nv * 55)     # 200〜255
        g = int(210 + nv * 45)     # 210〜255
        b = int(220 + nv * 35)     # 220〜255
    elif palette == "night":
        # 夜空っぽい色
        r = int(10 + nv * 40)      # 10〜50
        g = int(20 + nv * 60)      # 20〜80
        b = int(60 + nv * 160)     # 60〜220
    else:
        # デフォルトはファンタジー緑
        r = int(40 + nv * 80)
        g = int(80 + nv * 140)
        b = int(30 + nv * 80)

    # clamp
    r = clamp_int(r, 0, 255)
    g = clamp_int(g, 0, 255)
    b = clamp_int(b, 0, 255)
    return (r, g, b)

def generate_perlin_image(width: int, height: int, octaves: int, seed: Optional[int], palette: str) -> Image.Image:
    """
    PerlinNoise を使って画像を生成して返す。
    width, height: 画像サイズ
    octaves: PerlinNoise の octaves
    seed: 乱数シード（None の場合ランダム生成）
    palette: カラーパレット名
    """
    if seed is None:
        seed = random.randint(0, 2**31 - 1)
    logger.info("Generating image width=%d height=%d octaves=%d seed=%d palette=%s", width, height, octaves, seed)

    try:
        noise = PerlinNoise(octaves=octaves, seed=seed)
    except Exception:
        # PerlinNoise の初期化に失敗した場合は例外を投げる
        logger.exception("PerlinNoise の初期化に失敗しました。")
        raise

    img = Image.new("RGB", (width, height))
    pixels = img.load()

    # スケールを調整して見た目を良くする
    x_scale = 1.0 / max(1, width / 256.0)
    y_scale = 1.0 / max(1, height / 256.0)

    for y in range(height):
        for x in range(width):
            nx = x * x_scale / width
            ny = y * y_scale / height
            try:
                n = noise([nx, ny])
            except Exception:
                # PerlinNoise 呼び出しで失敗した場合は 0 を使う
                n = 0.0
            color = map_noise_to_color(n, palette)
            pixels[x, y] = color

    # 画像にメタ情報を付ける（Pillow の info に保存）
    img.info["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    img.info["seed"] = str(seed)
    img.info["palette"] = palette
    img.info["octaves"] = str(octaves)
    return img

def safe_save_image(img: Image.Image, path: str) -> None:
    """
    画像を安全に保存する。失敗したら例外を投げる。
    """
    try:
        img.save(path)
        logger.info("Saved image to %s", path)
    except Exception:
        logger.exception("画像の保存に失敗しました: %s", path)
        raise

class BGGeneratorGUI:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.repo_name = get_repo_name()
        self.master.title(f"RPG Background Generator - {self.repo_name}")
        self.master.geometry("420x320")
        self.master.resizable(False, False)

        # UI 要素
        self._build_widgets()

    def _build_widgets(self):
        pad = 8
        frame = tk.Frame(self.master)
        frame.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)

        # リポジトリ名表示
        lbl_repo = tk.Label(frame, text=f"Repository: {self.repo_name}", font=("Segoe UI", 11, "bold"))
        lbl_repo.pack(anchor="w", pady=(0, 6))

        # サイズ入力
        size_frame = tk.Frame(frame)
        size_frame.pack(fill=tk.X, pady=(0, 6))
        tk.Label(size_frame, text="Width", width=8).pack(side=tk.LEFT)
        self.entry_width = tk.Entry(size_frame, width=8)
        self.entry_width.insert(0, str(DEFAULT_WIDTH))
        self.entry_width.pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(size_frame, text="Height", width=8).pack(side=tk.LEFT)
        self.entry_height = tk.Entry(size_frame, width=8)
        self.entry_height.insert(0, str(DEFAULT_HEIGHT))
        self.entry_height.pack(side=tk.LEFT)

        # パレット選択
        palette_frame = tk.Frame(frame)
        palette_frame.pack(fill=tk.X, pady=(0, 6))
        tk.Label(palette_frame, text="Palette", width=8).pack(side=tk.LEFT)
        self.palette_var = tk.StringVar(value="forest")
        palettes = ["forest", "desert", "snow", "night"]
        self.palette_menu = tk.OptionMenu(palette_frame, self.palette_var, *palettes)
        self.palette_menu.config(width=12)
        self.palette_menu.pack(side=tk.LEFT)

        # Octaves と seed
        param_frame = tk.Frame(frame)
        param_frame.pack(fill=tk.X, pady=(0, 6))
        tk.Label(param_frame, text="Octaves", width=8).pack(side=tk.LEFT)
        self.entry_octaves = tk.Entry(param_frame, width=8)
        self.entry_octaves.insert(0, str(DEFAULT_OCTAVES))
        self.entry_octaves.pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(param_frame, text="Seed", width=8).pack(side=tk.LEFT)
        self.entry_seed = tk.Entry(param_frame, width=12)
        self.entry_seed.insert(0, "")  # 空ならランダム
        self.entry_seed.pack(side=tk.LEFT)

        # 出力ファイル名
        out_frame = tk.Frame(frame)
        out_frame.pack(fill=tk.X, pady=(0, 6))
        tk.Label(out_frame, text="Output", width=8).pack(side=tk.LEFT)
        self.entry_output = tk.Entry(out_frame, width=28)
        default_name = f"{self.repo_name}_background.png"
        self.entry_output.insert(0, default_name)
        self.entry_output.pack(side=tk.LEFT, padx=(0, 6))
        btn_browse = tk.Button(out_frame, text="参照", command=self._choose_output_path)
        btn_browse.pack(side=tk.LEFT)

        # ボタン群
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(12, 0))
        btn_generate = tk.Button(btn_frame, text="生成", width=12, command=self.on_generate)
        btn_generate.pack(side=tk.LEFT, padx=(0, 8))
        btn_preview = tk.Button(btn_frame, text="プレビュー生成のみ", width=16, command=self.on_preview)
        btn_preview.pack(side=tk.LEFT, padx=(0, 8))
        btn_quit = tk.Button(btn_frame, text="終了", width=8, command=self.master.quit)
        btn_quit.pack(side=tk.RIGHT)

        # ステータスバー
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(self.master, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _choose_output_path(self):
        initial = os.path.join(os.getcwd(), self.entry_output.get())
        filetypes = [("PNG Image", "*.png"), ("All files", "*.*")]
        path = filedialog.asksaveasfilename(title="出力ファイルを選択", initialfile=initial, defaultextension=".png", filetypes=filetypes)
        if path:
            self.entry_output.delete(0, tk.END)
            self.entry_output.insert(0, path)

    def _set_status(self, text: str):
        self.status_var.set(text)
        self.master.update_idletasks()

    def on_preview(self):
        """
        プレビュー生成は一時ファイルに保存せず、Pillow の show() を使って表示する。
        """
        try:
            width, height, octaves, seed, palette = self._gather_inputs()
            self._set_status("プレビュー生成中...")
            img = generate_perlin_image(width, height, octaves, seed, palette)
            # Pillow の show は一時ファイルを作って既定のビューアで開く
            img.show()
            self._set_status("プレビュー表示完了")
            logger.info("Preview generated (not saved).")
        except Exception as e:
            logger.exception("プレビュー生成中にエラーが発生しました。")
            messagebox.showerror("エラー", f"プレビュー生成に失敗しました。\n\n{str(e)}")
            self._set_status("Error")

    def on_generate(self):
        """
        実際にファイルとして保存する処理。
        """
        try:
            width, height, octaves, seed, palette = self._gather_inputs()
            out_path = self.entry_output.get().strip()
            if not out_path:
                messagebox.showwarning("出力ファイル未指定", "出力ファイル名を指定してください。")
                return
            # 拡張子がない場合は .png を付与
            if not os.path.splitext(out_path)[1]:
                out_path = out_path + ".png"

            # 保存先ディレクトリが存在しない場合は作成を促す
            out_dir = os.path.dirname(out_path) or os.getcwd()
            if out_dir and not os.path.exists(out_dir):
                try:
                    os.makedirs(out_dir, exist_ok=True)
                except Exception:
                    logger.exception("出力ディレクトリの作成に失敗しました: %s", out_dir)
                    messagebox.showerror("エラー", f"出力ディレクトリを作成できませんでした: {out_dir}")
                    return

            self._set_status("画像生成中...")
            img = generate_perlin_image(width, height, octaves, seed, palette)
            self._set_status("画像保存中...")
            safe_save_image(img, out_path)
            self._set_status("完了")
            messagebox.showinfo("完了", f"画像を生成しました。\n\n{out_path}")
            logger.info("Image generated and saved: %s", out_path)
        except ValueError as ve:
            logger.exception("入力値エラー")
            messagebox.showwarning("入力エラー", f"入力値が不正です。\n\n{str(ve)}")
            self._set_status("Input Error")
        except Exception as e:
            logger.exception("生成中に予期せぬエラーが発生しました。")
            tb = traceback.format_exc()
            messagebox.showerror("エラー", f"画像生成中にエラーが発生しました。\n\n{str(e)}\n\n詳細はログを確認してください。")
            self._set_status("Error")

    def _gather_inputs(self) -> Tuple[int, int, int, Optional[int], str]:
        """
        UI から入力を取得して検証する。
        戻り値: width, height, octaves, seed(Noneならランダム), palette
        """
        # width
        w_text = self.entry_width.get().strip()
        h_text = self.entry_height.get().strip()
        oct_text = self.entry_octaves.get().strip()
        seed_text = self.entry_seed.get().strip()
        palette = self.palette_var.get().strip()

        if not w_text.isdigit():
            raise ValueError("Width は正の整数で指定してください。")
        if not h_text.isdigit():
            raise ValueError("Height は正の整数で指定してください。")
        if not oct_text.isdigit():
            raise ValueError("Octaves は正の整数で指定してください。")

        width = int(w_text)
        height = int(h_text)
        octaves = int(oct_text)

        if width <= 0 or height <= 0:
            raise ValueError("Width と Height は正の値でなければなりません。")
        if octaves <= 0:
            raise ValueError("Octaves は 1 以上の整数でなければなりません。")

        seed: Optional[int]
        if seed_text == "":
            seed = None
        else:
            # seed は整数であることを保証する
            try:
                seed = int(seed_text)
            except Exception:
                raise ValueError("Seed は整数で指定してください。")

        # palette の検証
        if palette not in ("forest", "desert", "snow", "night"):
            raise ValueError("Palette は forest, desert, snow, night のいずれかを選択してください。")

        return width, height, octaves, seed, palette

def main():
    try:
        root = tk.Tk()
        app = BGGeneratorGUI(root)
        root.protocol("WM_DELETE_WINDOW", root.quit)
        root.mainloop()
    except Exception:
        # GUI の初期化や実行中に致命的なエラーが発生した場合はログに残して終了
        logger.exception("アプリケーションが致命的なエラーで終了しました。")
        # 可能ならユーザーにメッセージを出す
        try:
            tmp_root = tk.Tk()
            tmp_root.withdraw()
            messagebox.showerror("致命的エラー", "アプリケーションが致命的なエラーで終了しました。詳細はログを確認してください。")
            tmp_root.destroy()
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()

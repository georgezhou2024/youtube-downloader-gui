"""
YouTube 下载器 - 基于 yt-dlp 的图形界面下载工具
支持 mp3 音频提取 / mp4 4K 超高清视频下载
"""
import os
import sys
import threading
import subprocess
import urllib.request
import json
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 尝试导入 ttkbootstrap，没有就用标准 ttk
try:
    from ttkbootstrap import Style
    HAS_BOOTSTRAP = True
except ImportError:
    HAS_BOOTSTRAP = False

APP_NAME = "YouTube 下载器"
APP_VERSION = "1.4.0"

# 资源路径（打包后兼容：优先从 exe 同目录找，找不到再从打包临时目录找）
def resource_path(relative_path):
    # 获取 exe 所在目录（打包后）或脚本所在目录（开发时）
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(base_dir, relative_path)
    if os.path.exists(local_path):
        return local_path
    # PyInstaller 打包的资源在 _MEIPASS 里
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return local_path


class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("680x520")
        self.root.resizable(False, False)

        # 设置图标
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # 下载进程
        self.process = None
        self.is_downloading = False

        self._build_ui()

        # 启动后台检查更新
        threading.Thread(target=self._check_update, daemon=True).start()

    def _check_update(self):
        """后台检查 GitHub 最新版本"""
        try:
            api_url = "https://api.github.com/repos/georgezhou2024/youtube-downloader-gui/releases/latest"
            req = urllib.request.Request(api_url, headers={"User-Agent": "YouTube-Downloader"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            latest_version = data.get("tag_name", "").lstrip("v")
            release_url = data.get("html_url", "")

            if self._compare_version(latest_version, APP_VERSION) > 0:
                self.root.after(0, lambda: self._show_update_dialog(latest_version, release_url))
        except Exception:
            pass  # 网络错误静默忽略

    def _compare_version(self, v1, v2):
        """比较版本号，v1>v2 返回 1，相等返回 0，v1<v2 返回 -1"""
        try:
            a = [int(x) for x in v1.split(".")]
            b = [int(x) for x in v2.split(".")]
            for i in range(max(len(a), len(b))):
                ai = a[i] if i < len(a) else 0
                bi = b[i] if i < len(b) else 0
                if ai > bi: return 1
                if ai < bi: return -1
            return 0
        except Exception:
            return 0

    def _show_update_dialog(self, latest_version, release_url):
        """显示更新提示"""
        result = messagebox.askyesno(
            "发现新版本",
            f"当前版本: v{APP_VERSION}\n最新版本: v{latest_version}\n\n是否前往下载？"
        )
        if result:
            webbrowser.open(release_url)

    def _manual_check_update(self):
        """手动检查更新"""
        self._log("正在检查更新...")
        try:
            api_url = "https://api.github.com/repos/georgezhou2024/youtube-downloader-gui/releases/latest"
            req = urllib.request.Request(api_url, headers={"User-Agent": "YouTube-Downloader"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            latest_version = data.get("tag_name", "").lstrip("v")
            release_url = data.get("html_url", "")

            if self._compare_version(latest_version, APP_VERSION) > 0:
                self._log(f"发现新版本 v{latest_version}")
                result = messagebox.askyesno(
                    "发现新版本",
                    f"当前版本: v{APP_VERSION}\n最新版本: v{latest_version}\n\n是否前往下载？"
                )
                if result:
                    webbrowser.open(release_url)
            else:
                self._log(f"当前已是最新版本 v{APP_VERSION}")
                messagebox.showinfo("检查更新", f"当前已是最新版本 v{APP_VERSION}")
        except Exception as e:
            self._log(f"检查更新失败: {e}")
            messagebox.showerror("检查更新", f"检查失败: {e}")

    def _build_ui(self):
        # 主容器
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # 标题栏
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 15))

        title_label = ttk.Label(header, text="YouTube 视频下载器", font=("Microsoft YaHei UI", 17, "bold"))
        title_label.pack(side=tk.LEFT)

        version_label = ttk.Label(header, text=f"v{APP_VERSION}", foreground="#888", font=("Microsoft YaHei UI", 10))
        version_label.pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Label(header, text="皮肤：").pack(side=tk.RIGHT, padx=(0, 3))
        self.theme_var = tk.StringVar(value="暗黑")
        theme_combo = ttk.Combobox(header, textvariable=self.theme_var,
            values=["暗黑", "白色", "蓝色", "绿色", "红色"], state="readonly", width=6, font=("Microsoft YaHei UI", 9))
        theme_combo.pack(side=tk.RIGHT, padx=(0, 10))
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self._switch_theme())

        check_btn = ttk.Button(header, text="检查更新", command=self._manual_check_update)
        check_btn.pack(side=tk.RIGHT, padx=(0, 10))

        # URL 输入区
        url_frame = ttk.LabelFrame(main, text="视频链接", padding=10)
        url_frame.pack(fill=tk.X, pady=(0, 10))

        self.url_var = tk.StringVar(value="粘贴 YouTube / B站 / 全网视频链接...")
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Microsoft YaHei UI", 12))
        self.url_entry.pack(fill=tk.X, ipady=6)
        self.url_entry.bind("<FocusIn>", lambda e: self._clear_placeholder())

        # 选项区
        opt_frame = ttk.LabelFrame(main, text="下载选项", padding=10)
        opt_frame.pack(fill=tk.X, pady=(0, 10))

        # 格式选择
        format_row = ttk.Frame(opt_frame)
        format_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(format_row, text="下载格式：", font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value="mp3")
        ttk.Radiobutton(format_row, text="MP3 音频", variable=self.format_var, value="mp3", command=self._on_format_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_row, text="MP4 视频", variable=self.format_var, value="mp4", command=self._on_format_change).pack(side=tk.LEFT, padx=(10, 20))

        # 分辨率选择（仅 mp4 显示）
        ttk.Label(format_row, text="分辨率：", font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT)
        self.resolution_var = tk.StringVar(value="最高画质")
        self.resolution_combo = ttk.Combobox(format_row, textvariable=self.resolution_var,
            values=["最高画质", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p"],
            state="readonly", width=14, font=("Microsoft YaHei UI", 10))
        self.resolution_combo.pack(side=tk.LEFT, padx=(5, 0))

        # 输出路径
        path_row = ttk.Frame(opt_frame)
        path_row.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(path_row, text="保存位置：", font=("Microsoft YaHei UI", 11)).pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value="G:\\模型")
        path_entry = ttk.Entry(path_row, textvariable=self.path_var, font=("Microsoft YaHei UI", 11))
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5), ipady=4)
        browse_btn = ttk.Button(path_row, text="浏览...", command=self._browse_folder)
        browse_btn.pack(side=tk.RIGHT)

        # 按钮区
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(5, 10))

        self.download_btn = ttk.Button(btn_frame, text="开始下载", command=self._start_download, style="Accent.TButton")
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.cancel_btn = ttk.Button(btn_frame, text="取消", command=self._cancel_download, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.open_folder_btn = ttk.Button(btn_frame, text="打开文件夹", command=self._open_output_folder, state=tk.DISABLED)
        self.open_folder_btn.pack(side=tk.LEFT)

        # 自定义进度条（Canvas 画绿色渐变 + 百分比）
        progress_frame = ttk.LabelFrame(main, text="下载进度", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_canvas = tk.Canvas(progress_frame, height=36, bg="#2d2d30", highlightthickness=0)
        self.progress_canvas.pack(fill=tk.X)
        self.progress_var = tk.DoubleVar(value=0)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var, foreground="#aaa", font=("Microsoft YaHei UI", 10))
        status_label.pack(anchor=tk.W, pady=(5, 0))

        # 日志区
        log_frame = ttk.LabelFrame(main, text="日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=7, wrap=tk.WORD, font=("Cascadia Code", 10), state=tk.DISABLED,
                                bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 初始绘制进度条背景
        self._draw_progress(0)

    def _clear_placeholder(self):
        if self.url_var.get() == "粘贴 YouTube / B站 / 全网视频链接...":
            self.url_var.set("")

    def _on_format_change(self):
        # mp3 模式下禁用分辨率选择
        if self.format_var.get() == "mp3":
            self.resolution_combo.configure(state="disabled")
        else:
            self.resolution_combo.configure(state="readonly")

    def _draw_progress(self, pct):
        """画绿色渐变进度条 + 百分比文字（节流防闪烁）"""
        self.progress_var.set(pct)
        # 用 after 节流，最多每 100ms 重绘一次
        if hasattr(self, '_progress_after_id'):
            self.root.after_cancel(self._progress_after_id)
        self._progress_after_id = self.root.after(50, lambda: self._do_draw(pct))

    def _do_draw(self, pct):
        """实际绘制进度条"""
        self.progress_canvas.delete("all")
        w = self.progress_canvas.winfo_width()
        if w < 10:
            w = 600
        h = 36
        fill_w = int(w * pct / 100)

        self.progress_canvas.create_rectangle(0, 0, w, h, fill="#3c3c3f", outline="")

        if fill_w > 0:
            steps = 20
            for i in range(steps):
                x0 = int(fill_w * i / steps)
                x1 = int(fill_w * (i + 1) / steps)
                r = int(60 + i * 3)
                g = int(180 + i * 2)
                b = int(80 - i * 2)
                color = f"#{r:02x}{g:02x}{b:02x}"
                self.progress_canvas.create_rectangle(x0, 0, x1, h, fill=color, outline="")

        text = f"{pct:.1f}%" if pct > 0 else ""
        if text:
            self.progress_canvas.create_text(w // 2, h // 2, text=text, fill="white",
                                            font=("Microsoft YaHei UI", 12, "bold"))

    def _switch_theme(self):
        """切换主题皮肤"""
        theme_map = {
            "暗黑": "darkly",
            "白色": "litera",
            "蓝色": "cosmo",
            "绿色": "flatly",
            "红色": "pulse"
        }
        theme = theme_map.get(self.theme_var.get(), "darkly")
        if HAS_BOOTSTRAP:
            from ttkbootstrap import Style
            style = Style(theme=theme)
            # 更新进度条颜色
            self._draw_progress(self.progress_var.get())

    def _open_output_folder(self):
        """打开输出文件夹"""
        folder = self.path_var.get()
        if os.path.isdir(folder):
            os.startfile(folder)

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.path_var.get())
        if folder:
            self.path_var.set(folder)

    def _log(self, msg):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def _build_command(self, url):
        """构建 yt-dlp 命令"""
        ytdlp = resource_path("yt-dlp.exe")
        ffmpeg_dir = resource_path("ffmpeg")

        if not os.path.exists(ytdlp):
            ytdlp = "yt-dlp"

        cmd = [ytdlp, "--no-playlist", "--newline", "--concurrent-fragments", "5"]

        if self.format_var.get() == "mp3" or getattr(self, "_selected_quality", "") == "audio":
            cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0"])
        else:
            # 根据用户选择的分辨率
            q = getattr(self, "_selected_quality", "best")
            if q == "best":
                fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            elif q and q.isdigit():
                h = int(q)
                fmt = f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/best[height<={h}]/best"
            else:
                fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            cmd.extend(["-f", fmt, "--merge-output-format", "mp4"])

        if os.path.exists(ffmpeg_dir):
            cmd.extend(["--ffmpeg-location", ffmpeg_dir])

        out_path = os.path.join(self.path_var.get(), "%(title)s.%(ext)s")
        cmd.extend(["-o", out_path])
        cmd.append(url)

        return cmd

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url or url == "粘贴 YouTube / B站 / 全网视频链接...":
            messagebox.showwarning("提示", "请先粘贴视频链接")
            return

        if not os.path.isdir(self.path_var.get()):
            messagebox.showerror("错误", "保存位置不存在，请重新选择")
            return

        # mp4 模式：先获取视频信息，弹窗选分辨率
        if self.format_var.get() == "mp4":
            self.status_var.set("正在获取视频信息...")
            self._log("正在获取视频信息...")
            threading.Thread(target=self._fetch_and_show_quality, args=(url,), daemon=True).start()
        else:
            self._do_download(url, self.resolution_var.get())

    def _fetch_and_show_quality(self, url):
        """获取视频信息并弹出分辨率选择窗口"""
        try:
            ytdlp = resource_path("yt-dlp.exe")
            if not os.path.exists(ytdlp):
                ytdlp = "yt-dlp"

            # 获取视频信息 JSON
            cmd = [ytdlp, "-J", "--no-playlist", url]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
            if result.returncode != 0:
                self.root.after(0, lambda: messagebox.showerror("错误", f"获取视频信息失败:\n{result.stderr[:200]}"))
                return

            info = json.loads(result.stdout)
            title = info.get("title", "未知标题")
            duration = info.get("duration", 0)
            formats = info.get("formats", [])

            # 提取视频格式（有高度的）
            video_formats = []
            seen_res = set()
            for f in formats:
                h = f.get("height")
                if h and h not in seen_res:
                    seen_res.add(h)
                    size = f.get("filesize") or f.get("filesize_approx") or 0
                    ext = f.get("ext", "mp4")
                    vcodec = f.get("vcodec", "")[:12]
                    video_formats.append({"height": h, "size": size, "ext": ext, "vcodec": vcodec})
            video_formats.sort(key=lambda x: x["height"], reverse=True)

            # 在主线程弹窗
            self.root.after(0, lambda: self._show_quality_dialog(url, title, duration, video_formats))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"获取视频信息失败: {e}"))

    def _show_quality_dialog(self, url, title, duration, formats):
        """显示分辨率选择窗口"""
        dlg = tk.Toplevel(self.root)
        dlg.title("选择分辨率")
        dlg.geometry("520x560")
        dlg.transient(self.root)
        dlg.grab_set()

        # 标题
        ttk.Label(dlg, text=title, font=("Microsoft YaHei UI", 12, "bold"), wraplength=480).pack(anchor=tk.W, padx=15, pady=(15, 5))
        mins = duration // 60 if duration else 0
        secs = duration % 60 if duration else 0
        ttk.Label(dlg, text=f"时长: {mins}:{secs:02d}", foreground="#888").pack(anchor=tk.W, padx=15)

        # 滚动列表
        canvas = tk.Canvas(dlg, bg="#2d2d30", highlightthickness=0)
        scrollbar = ttk.Scrollbar(dlg, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=10)
        scrollbar.pack(side="right", fill="y")

        selected = tk.StringVar(value="best")

        # 最高画质选项
        rb = ttk.Radiobutton(frame, text="最高画质（自动合并音视频）", variable=selected, value="best")
        rb.pack(anchor=tk.W, pady=5)
        ttk.Label(frame, text="推荐 · bestvideo+bestaudio", foreground="#888").pack(anchor=tk.W, padx=20)

        ttk.Separator(frame).pack(fill="x", pady=8)

        # 各分辨率选项
        max_h = max(f["height"] for f in formats) if formats else 1080
        for f in formats:
            h = f["height"]
            size_mb = f["size"] / 1024 / 1024 if f["size"] else 0
            size_str = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{size_mb/1024:.2f} GB"
            text = f"{h}p"
            sub = f"{f['ext']} · {f['vcodec']} · {size_str}"
            rb = ttk.Radiobutton(frame, text=text, variable=selected, value=str(h))
            rb.pack(anchor=tk.W, pady=3)
            ttk.Label(frame, text=sub, foreground="#888").pack(anchor=tk.W, padx=20)

        # 仅音频
        ttk.Separator(frame).pack(fill="x", pady=8)
        ttk.Radiobutton(frame, text="仅音频 (MP3)", variable=selected, value="audio").pack(anchor=tk.W, pady=3)

        # 底部按钮
        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill="x", padx=15, pady=10)
        ttk.Button(btn_frame, text="取消", command=dlg.destroy).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="下载", style="Accent.TButton",
                   command=lambda: self._on_quality_selected(dlg, url, selected.get())).pack(side="right")

    def _on_quality_selected(self, dlg, url, quality):
        dlg.destroy()
        self._do_download(url, quality)

    def _do_download(self, url, quality):
        """实际开始下载"""
        self.is_downloading = True
        self.download_btn.configure(state=tk.DISABLED)
        self.cancel_btn.configure(state=tk.NORMAL)
        self.open_folder_btn.configure(state=tk.DISABLED)
        self._draw_progress(0)
        self.status_var.set("正在下载...")
        self._log(f"开始下载: {url}")
        self._log(f"格式: {self.format_var.get().upper()}, 分辨率: {quality}, 保存到: {self.path_var.get()}")

        # 把用户选的分辨率存起来
        self._selected_quality = quality

        thread = threading.Thread(target=self._download_worker, args=(url,), daemon=True)
        thread.start()

    def _download_worker(self, url):
        try:
            cmd = self._build_command(url)
            self._log("执行: " + " ".join(cmd))

            # 用 Popen 实时读取输出（yt-dlp 在 Windows 输出 GBK 编码）
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="gbk",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            for line in self.process.stdout:
                line = line.strip()
                if not line:
                    continue
                self._log(line)

                # 解析进度百分比
                if "[download]" in line and "%" in line:
                    try:
                        pct_str = line.split("%")[0].split()[-1]
                        pct = float(pct_str)
                        self._draw_progress(pct)
                    except (ValueError, IndexError):
                        pass

            self.process.wait()

            if self.process.returncode == 0:
                self._draw_progress(100)
                self.status_var.set("下载完成！")
                self.open_folder_btn.configure(state=tk.NORMAL)
                self._log("=== 下载完成 ===")
                messagebox.showinfo("完成", f"下载完成！\n文件已保存到:\n{self.path_var.get()}")
            else:
                self.status_var.set("下载失败")
                self._log(f"=== 下载失败，退出码: {self.process.returncode} ===")
                messagebox.showerror("错误", f"下载失败，退出码: {self.process.returncode}\n请查看日志了解详情。")

        except Exception as e:
            self.status_var.set("出错了")
            self._log(f"错误: {e}")
            messagebox.showerror("错误", str(e))
        finally:
            self.is_downloading = False
            self.download_btn.configure(state=tk.NORMAL)
            self.cancel_btn.configure(state=tk.DISABLED)
            self.process = None

    def _cancel_download(self):
        if self.process and self.is_downloading:
            self.process.terminate()
            self._log("=== 用户取消下载 ===")
            self.status_var.set("已取消")


def main():
    if HAS_BOOTSTRAP:
        style = Style(theme="darkly")
        root = style.master
    else:
        root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

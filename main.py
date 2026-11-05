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
APP_VERSION = "1.2.0"

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

        # 标题栏（左标题 + 右版本号/检查更新）
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 15))

        title_label = ttk.Label(header, text="YouTube 视频下载器", font=("Microsoft YaHei UI", 16, "bold"))
        title_label.pack(side=tk.LEFT)

        version_label = ttk.Label(header, text=f"v{APP_VERSION}", foreground="#888", font=("Microsoft YaHei UI", 10))
        version_label.pack(side=tk.RIGHT, padx=(5, 0))

        check_btn = ttk.Button(header, text="检查更新", command=self._manual_check_update)
        check_btn.pack(side=tk.RIGHT, padx=(0, 10))

        # URL 输入区
        url_frame = ttk.LabelFrame(main, text="视频链接", padding=10)
        url_frame.pack(fill=tk.X, pady=(0, 10))

        self.url_var = tk.StringVar(value="粘贴 YouTube / B站 / 全网视频链接...")
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Microsoft YaHei UI", 11))
        self.url_entry.pack(fill=tk.X, ipady=5)
        self.url_entry.bind("<FocusIn>", lambda e: self._clear_placeholder())

        # 选项区
        opt_frame = ttk.LabelFrame(main, text="下载选项", padding=10)
        opt_frame.pack(fill=tk.X, pady=(0, 10))

        # 格式选择
        format_row = ttk.Frame(opt_frame)
        format_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(format_row, text="下载格式：").pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value="mp3")
        ttk.Radiobutton(format_row, text="MP3 音频", variable=self.format_var, value="mp3", command=self._on_format_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_row, text="MP4 视频（最高画质）", variable=self.format_var, value="mp4", command=self._on_format_change).pack(side=tk.LEFT, padx=10)

        # 输出路径
        path_row = ttk.Frame(opt_frame)
        path_row.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(path_row, text="保存位置：").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value="G:\\模型")
        path_entry = ttk.Entry(path_row, textvariable=self.path_var)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5), ipady=3)
        browse_btn = ttk.Button(path_row, text="浏览...", command=self._browse_folder)
        browse_btn.pack(side=tk.RIGHT)

        # 按钮区
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(5, 10))

        self.download_btn = ttk.Button(btn_frame, text="开始下载", command=self._start_download, style="Accent.TButton")
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.cancel_btn = ttk.Button(btn_frame, text="取消", command=self._cancel_download, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT)

        # 进度条
        progress_frame = ttk.LabelFrame(main, text="下载进度", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, style="success.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, ipady=3)

        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var, foreground="#aaa")
        status_label.pack(anchor=tk.W, pady=(5, 0))

        # 日志区
        log_frame = ttk.LabelFrame(main, text="日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD, font=("Consolas", 9), state=tk.DISABLED, bg="#1e1e1e", fg="#d4d4d4", insertbackground="#d4d4d4")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _clear_placeholder(self):
        if self.url_var.get() == "粘贴 YouTube / B站 / 全网视频链接...":
            self.url_var.set("")

    def _on_format_change(self):
        pass

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

        # 备用：系统 PATH 里找
        if not os.path.exists(ytdlp):
            ytdlp = "yt-dlp"

        cmd = [ytdlp, "--no-playlist", "--newline"]

        if self.format_var.get() == "mp3":
            # 提取音频，转 mp3
            cmd.extend([
                "-x", "--audio-format", "mp3",
                "--audio-quality", "0",
            ])
        else:
            # 视频：最高画质 + 合并音频
            cmd.extend([
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
            ])

        # ffmpeg 路径
        if os.path.exists(ffmpeg_dir):
            cmd.extend(["--ffmpeg-location", ffmpeg_dir])

        # 输出模板
        out_path = os.path.join(self.path_var.get(), "%(title)s.%(ext)s")
        cmd.extend(["-o", out_path])

        # URL
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

        self.is_downloading = True
        self.download_btn.configure(state=tk.DISABLED)
        self.cancel_btn.configure(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_var.set("正在下载...")
        self._log(f"开始下载: {url}")
        self._log(f"格式: {self.format_var.get().upper()}, 保存到: {self.path_var.get()}")

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
                        self.progress_var.set(pct)
                    except (ValueError, IndexError):
                        pass

            self.process.wait()

            if self.process.returncode == 0:
                self.progress_var.set(100)
                self.status_var.set("下载完成！")
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

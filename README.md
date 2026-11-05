# YouTube 下载器

基于 yt-dlp 的 Windows 图形界面视频下载工具，支持全网 1000+ 网站。

## 功能

- **MP3 音频提取**：一键提取音频，自动转 mp3
- **MP4 超高清下载**：自动选择最高画质（最高 4K）
- **自定义保存路径**：自由选择下载目录
- **全网支持**：YouTube、B站、Twitter、TikTok、抖音、小红书等 1000+ 网站

## 使用方法

1. 下载 Release 里的完整压缩包
2. 解压到任意目录
3. 双击 `YouTube下载器.exe`
4. 粘贴视频链接，选择格式，点击"开始下载"

## 目录结构

```
YouTube下载器.exe    # 主程序
yt-dlp.exe          # 下载核心
ffmpeg/ffmpeg.exe   # 转码工具
```

## 技术栈

- Python + tkinter
- yt-dlp（下载核心）
- ffmpeg（音频提取 / 视频合并）
- PyInstaller（打包）

## License

MIT

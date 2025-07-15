# FTP Sync Tool

Lightning-fast FTP synchronization that tracks only what's changed. No more waiting for slow server comparisons.

## The Problem

Traditional FTP clients waste your time:
- Compare every single file with the server (2-5 minutes)
- Re-upload files that haven't changed
- Manual selection of changed files
- Slow deployment = interrupted workflow

## The Solution

FTP Sync Tool tracks changes **locally** using file hashes:
- Detect changes in 2 seconds (not minutes!)
- Upload only modified files
- One-click sync
- Remember multiple project configurations

## Features

- **⚡ Fast**: Local change detection, no server queries
- **🎯 Smart**: Tracks file modifications between sessions
- **📁 Multi-project**: Save unlimited FTP configurations
- **🚫 Auto-ignore**: Skips .git, node_modules automatically
- **📊 Progress tracking**: See exactly what's uploading

## Download

- [Windows](https://github.com/mansourjabin/ftp-sync-tool/releases/latest/download/ftp-sync-windows.exe)
- [Linux](https://github.com/mansourjabin/ftp-sync-tool/releases/latest/download/ftp-sync-linux)
- [macOS](https://github.com/mansourjabin/ftp-sync-tool/releases/latest/download/ftp-sync-macos)

## Quick Start

```bash
# First run - setup takes 30 seconds
./ftp-sync-linux

# Enter your project details:
Folder: /path/to/your/project
FTP Server: ftp.yoursite.com
Username: your-username
Password: ********

# Daily usage:
1. Make changes to your code
2. Run FTP Sync
3. Press "1" to sync
4. Done! Only changed files uploaded
```

## Perfect for Cursor Users 🎯

If you're using **Cursor AI** for rapid development, FTP Sync is your perfect deployment companion:

- **Problem**: Cursor generates/modifies many files quickly
- **Traditional FTP**: Can't keep up, takes forever to compare files
- **FTP Sync**: Instantly detects all Cursor's changes and uploads in seconds

**Workflow with Cursor:**
1. Let Cursor AI write/modify your code
2. Alt+Tab to FTP Sync
3. Press "1" - all changes deployed
4. Back to Cursor for more coding!

No more waiting. No more manual selection. Just code and deploy at the speed of thought.

---

Made with ❤️ and ⚡ passion • [GitHub](https://github.com/mansourjabin/ftp-sync-tool)

#!/usr/bin/env python3
import os
import sys
import time
import ftplib
import hashlib
from datetime import datetime
from pathlib import Path
import json
import argparse
import threading

# Try to import colorama for Windows color support
try:
    from colorama import init, Fore, Back, Style
    init()
except ImportError:
    # Fallback to ANSI codes
    class Fore:
        BLACK = '\033[30m'
        RED = '\033[31m'
        GREEN = '\033[32m'
        YELLOW = '\033[33m'
        BLUE = '\033[34m'
        MAGENTA = '\033[35m'
        CYAN = '\033[36m'
        WHITE = '\033[37m'
        RESET = '\033[39m'
        
    class Back:
        BLACK = '\033[40m'
        RED = '\033[41m'
        GREEN = '\033[42m'
        YELLOW = '\033[43m'
        BLUE = '\033[44m'
        MAGENTA = '\033[45m'
        CYAN = '\033[46m'
        WHITE = '\033[47m'
        RESET = '\033[49m'
        
    class Style:
        BRIGHT = '\033[1m'
        DIM = '\033[2m'
        NORMAL = '\033[22m'
        RESET_ALL = '\033[0m'

# Try to import readline for auto-complete
try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline
    except ImportError:
        readline = None

class UI:
    """Helper class for beautiful terminal UI"""
    
    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def header(text):
        width = 60
        print(f"\n{Fore.CYAN}{'═' * width}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Style.BRIGHT}{text.center(width-4)}{Style.NORMAL} {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═' * width}{Style.RESET_ALL}\n")
    
    @staticmethod
    def section(text):
        print(f"\n{Fore.YELLOW}>> {Style.BRIGHT}{text}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'-' * 40}{Style.RESET_ALL}")
    
    @staticmethod
    def success(text):
        print(f"{Fore.GREEN}[+] {text}{Style.RESET_ALL}")
    
    @staticmethod
    def error(text):
        print(f"{Fore.RED}[X] {text}{Style.RESET_ALL}")
    
    @staticmethod
    def warning(text):
        print(f"{Fore.YELLOW}[!] {text}{Style.RESET_ALL}")
    
    @staticmethod
    def info(text):
        print(f"{Fore.BLUE}[i] {text}{Style.RESET_ALL}")
    
    @staticmethod
    def prompt(text):
        return input(f"{Fore.MAGENTA}>>> {text}{Style.RESET_ALL}")
    
    @staticmethod
    def progress(current, total, text=""):
        bar_width = 30
        progress = current / total
        filled = int(bar_width * progress)
        bar = "#" * filled + "-" * (bar_width - filled)
        percentage = progress * 100
        print(f"\r{Fore.CYAN}[{bar}] {percentage:3.0f}% {text}{Style.RESET_ALL}", end='', flush=True)
        if current == total:
            print()  # New line when complete

class FolderWatcher:
    def __init__(self, watch_folder=None):
        self.watch_folder = watch_folder
        self.ftp_config = None
        self.file_hashes = {}
        # Store config in user's home directory
        self.config_dir = os.path.join(os.path.expanduser("~"), ".ftp_sync")
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Minimal ignore patterns
        self.ignore_patterns = [
            '.git', '.svn', 'node_modules', '.DS_Store', 'Thumbs.db',
            '__pycache__', '.idea', '.vscode',
            '*.pyc', '*.pyo', '.pytest_cache'
        ]
        
        # Create unique config file name based on folder path
        if watch_folder:
            folder_hash = hashlib.md5(watch_folder.encode()).hexdigest()[:8]
            self.config_file = os.path.join(self.config_dir, f"config_{folder_hash}.json")
        else:
            self.config_file = os.path.join(self.config_dir, "config_default.json")
        
    def setup(self):
        """Initial setup with beautiful UI"""
        UI.clear()
        UI.header("= FTP Sync Setup =")
        
        # Check if folder exists
        if not os.path.exists(self.watch_folder):
            UI.error(f"Folder {self.watch_folder} does not exist!")
            return False
        
        UI.success(f"Setting up sync for: {self.watch_folder}")
        
        # Get FTP info
        UI.section("FTP Server Configuration")
        
        self.ftp_config = {
            'host': UI.prompt("FTP server address: "),
            'port': int(UI.prompt("Port (press Enter for 21): ") or "21"),
            'username': UI.prompt("Username: "),
            'password': UI.prompt("Password: "),
            'remote_path': UI.prompt("Remote path (e.g. /public_html): ")
        }
        
        # Test connection
        UI.info("Testing FTP connection...")
        if self.test_connection():
            UI.success("Connection successful!")
        else:
            UI.error("Connection failed! Please check your settings.")
            retry = UI.prompt("Try again? (y/n): ")
            if retry.lower() == 'y':
                return self.setup()
            return False
        
        # Ask if user wants to mark existing files as already synced
        UI.section("Initial Scan")
        mark_existing = UI.prompt("Mark existing files as already synced? (recommended) (y/n): ")
        
        if mark_existing.lower() == 'y':
            UI.info("Scanning folder and marking existing files as synced...")
            self.scan_folder(save_changes=True, show_progress=True)
            UI.success(f"Marked {len(self.file_hashes)} existing files as synced!")
        else:
            UI.warning("All existing files will be uploaded on first sync!")
        
        # Save config
        self.save_config()
        UI.success(f"Configuration saved!")
        time.sleep(1)
        return True
        
    def test_connection(self):
        """Test FTP connection"""
        try:
            ftp = ftplib.FTP()
            ftp.connect(self.ftp_config['host'], self.ftp_config['port'], timeout=10)
            ftp.login(self.ftp_config['username'], self.ftp_config['password'])
            ftp.quit()
            return True
        except:
            return False
        
    def save_config(self):
        """Save configuration to file"""
        config = {
            'watch_folder': self.watch_folder,
            'ftp_config': self.ftp_config,
            'file_hashes': self.file_hashes
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
            
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.watch_folder = config['watch_folder']
                self.ftp_config = config['ftp_config']
                self.file_hashes = config.get('file_hashes', {})
                return True
        return False
        
    def get_file_hash(self, filepath):
        """Calculate file hash quickly"""
        hasher = hashlib.md5()
        file_size = os.path.getsize(filepath)
        
        with open(filepath, 'rb') as f:
            # Hash first 1MB
            hasher.update(f.read(1024 * 1024))
            
            # Hash last 1MB if file is larger
            if file_size > 2 * 1024 * 1024:
                f.seek(-1024 * 1024, 2)
                hasher.update(f.read(1024 * 1024))
                
            # Include file size and mtime
            hasher.update(str(file_size).encode())
            hasher.update(str(os.path.getmtime(filepath)).encode())
            
        return hasher.hexdigest()
        
    def should_ignore(self, filepath):
        """Check if file should be ignored"""
        parts = filepath.replace('\\', '/').split('/')
        
        for pattern in self.ignore_patterns:
            for part in parts:
                if pattern.startswith('*'):
                    if part.endswith(pattern[1:]):
                        return True
                elif pattern in part:
                    return True
        
        # Check file size (skip very large files)
        try:
            size = os.path.getsize(os.path.join(self.watch_folder, filepath))
            if size > 100 * 1024 * 1024:  # 100MB
                UI.warning(f"Skipping large file (>100MB): {filepath}")
                return True
        except:
            pass
            
        return False
    
    def scan_folder(self, save_changes=True, show_progress=False):
        """Scan folder with progress indicator"""
        current_files = {}
        changes = {'new': [], 'modified': []}
        skipped_files = []
        
        # Count total files first
        total_files = sum(len(files) for _, _, files in os.walk(self.watch_folder))
        current = 0
        
        for root, dirs, files in os.walk(self.watch_folder):
            # Remove ignored directories
            original_dirs = dirs[:]
            dirs[:] = [d for d in dirs if not self.should_ignore(d)]
            
            for file in files:
                current += 1
                if show_progress:
                    UI.progress(current, total_files, f"Scanning: {file[:30]}...")
                
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, self.watch_folder)
                
                if self.should_ignore(relative_path):
                    skipped_files.append(relative_path)
                    continue
                
                try:
                    file_hash = self.get_file_hash(filepath)
                    current_files[relative_path] = file_hash
                    
                    if relative_path not in self.file_hashes:
                        changes['new'].append(relative_path)
                    elif self.file_hashes[relative_path] != file_hash:
                        changes['modified'].append(relative_path)
                except Exception as e:
                    pass
        
        if save_changes:
            self.file_hashes = current_files
            self.save_config()
            
        return changes
        
    def connect_ftp(self):
        """Connect to FTP server"""
        try:
            ftp = ftplib.FTP()
            ftp.set_debuglevel(0)
            ftp.connect(self.ftp_config['host'], self.ftp_config['port'], timeout=30)
            ftp.login(self.ftp_config['username'], self.ftp_config['password'])
            ftp.voidcmd('TYPE I')
            
            try:
                ftp.sendcmd('OPTS UTF8 ON')
            except:
                pass
                
            return ftp
        except ftplib.error_perm as e:
            UI.error(f"FTP permission error: {e}")
            return None
        except Exception as e:
            UI.error(f"FTP connection error: {e}")
            return None
            
    def create_remote_dirs(self, ftp, remote_path):
        """Create necessary directories on server"""
        dirs = [d for d in remote_path.split('/') if d]
        
        if dirs:
            dirs = dirs[:-1]
        
        if self.ftp_config['remote_path']:
            ftp.cwd(self.ftp_config['remote_path'])
        else:
            ftp.cwd('/')
        
        for i, dir in enumerate(dirs):
            try:
                ftp.cwd(dir)
            except:
                try:
                    ftp.mkd(dir)
                    ftp.cwd(dir)
                except:
                    pass
                        
    def upload_file(self, ftp, local_file, remote_file):
        """Upload file to FTP server"""
        try:
            remote_file = remote_file.replace('\\', '/')
            self.create_remote_dirs(ftp, remote_file)
            
            if self.ftp_config['remote_path']:
                ftp.cwd(self.ftp_config['remote_path'])
            else:
                ftp.cwd('/')
            
            with open(local_file, 'rb') as f:
                ftp.storbinary(f'STOR {remote_file}', f)
            return True
        except Exception as e:
            try:
                dirs = [d for d in remote_file.split('/') if d]
                filename = dirs[-1] if dirs else remote_file
                dirs = dirs[:-1] if len(dirs) > 1 else []
                
                if self.ftp_config['remote_path']:
                    ftp.cwd(self.ftp_config['remote_path'])
                else:
                    ftp.cwd('/')
                    
                for dir in dirs:
                    try:
                        ftp.cwd(dir)
                    except:
                        ftp.mkd(dir)
                        ftp.cwd(dir)
                
                with open(local_file, 'rb') as f:
                    ftp.storbinary(f'STOR {filename}', f)
                return True
            except:
                return False
            
    def sync_changes(self):
        """Sync changes with beautiful progress"""
        UI.section("Scanning for changes")
        start_time = time.time()
        
        changes = self.scan_folder(save_changes=False, show_progress=True)
        
        scan_time = time.time() - start_time
        print()  # New line after progress
        UI.info(f"Scan completed in {scan_time:.2f} seconds")
        
        if not changes['new'] and not changes['modified']:
            UI.success("Everything is up to date!")
            return
            
        # Display changes
        total = len(changes['new']) + len(changes['modified'])
        UI.section(f"Found {total} changes")
        
        if changes['new']:
            print(f"\n{Fore.GREEN}New files ({len(changes['new'])}):{Style.RESET_ALL}")
            for file in changes['new'][:5]:
                print(f"   {Fore.GREEN}+{Style.RESET_ALL} {file}")
            if len(changes['new']) > 5:
                print(f"   {Fore.CYAN}... and {len(changes['new']) - 5} more{Style.RESET_ALL}")
                
        if changes['modified']:
            print(f"\n{Fore.BLUE}Modified files ({len(changes['modified'])}):{Style.RESET_ALL}")
            for file in changes['modified'][:5]:
                print(f"   {Fore.BLUE}M{Style.RESET_ALL} {file}")
            if len(changes['modified']) > 5:
                print(f"   {Fore.CYAN}... and {len(changes['modified']) - 5} more{Style.RESET_ALL}")
        
        confirm = UI.prompt("\nProceed with sync? (y/n): ")
        if confirm.lower() != 'y':
            UI.warning("Sync cancelled.")
            return
            
        UI.section("Uploading files")
        UI.info("Connecting to FTP server...")
        
        ftp = self.connect_ftp()
        if not ftp:
            return
            
        try:
            if self.ftp_config['remote_path']:
                try:
                    ftp.cwd(self.ftp_config['remote_path'])
                except:
                    self.create_remote_dirs(ftp, self.ftp_config['remote_path'] + '/dummy')
                    ftp.cwd(self.ftp_config['remote_path'])
                    
            current = 0
            success = 0
            failed_files = []
            
            # Upload all files
            all_files = [(f, 'new') for f in changes['new']] + [(f, 'modified') for f in changes['modified']]
            
            for file, change_type in all_files:
                current += 1
                local_path = os.path.join(self.watch_folder, file)
                
                # Show progress
                UI.progress(current, total, f"{file[:30]}...")
                
                if self.upload_file(ftp, local_path, file):
                    success += 1
                else:
                    failed_files.append(file)
                    
            print()  # New line after progress
            
            if success == total:
                UI.success(f"All {total} files uploaded successfully!")
            else:
                UI.warning(f"Uploaded {success}/{total} files")
                if failed_files:
                    UI.error(f"{len(failed_files)} files failed to upload")
            
            if success > 0:
                UI.info("Updating tracking database...")
                self.scan_folder(save_changes=True)
                    
        except Exception as e:
            UI.error(f"Sync error: {e}")
        finally:
            ftp.quit()
            
    def watch(self):
        """Main loop with beautiful menu"""
        while True:
            UI.clear()
            UI.header("== FTP Sync Manager ==")
            
            # Show status
            print(f"{Fore.CYAN}Folder:{Style.RESET_ALL} {self.watch_folder}")
            print(f"{Fore.CYAN}Server:{Style.RESET_ALL} {self.ftp_config['host']}")
            print(f"{Fore.CYAN}Remote:{Style.RESET_ALL} {self.ftp_config['remote_path']}")
            print(f"{Fore.CYAN}Tracked:{Style.RESET_ALL} {len(self.file_hashes)} files")
            
            # Quick status check
            changes = self.scan_folder(save_changes=False)
            pending = len(changes['new']) + len(changes['modified'])
            if pending > 0:
                print(f"\n{Fore.YELLOW}[!] {pending} changes pending!{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.GREEN}[+] Everything is synchronized{Style.RESET_ALL}")
            
            # Menu
            UI.section("Commands")
            print(f"  {Fore.GREEN}[1]{Style.RESET_ALL} Sync now")
            print(f"  {Fore.BLUE}[2]{Style.RESET_ALL} View detailed status")
            print(f"  {Fore.YELLOW}[3]{Style.RESET_ALL} Reset tracking")
            print(f"  {Fore.MAGENTA}[4]{Style.RESET_ALL} Settings")
            print(f"  {Fore.RED}[5]{Style.RESET_ALL} Delete this configuration")
            print(f"  {Fore.RED}[6]{Style.RESET_ALL} Exit")
            
            choice = UI.prompt("\nYour choice (1-6): ")
            
            if choice == '1':
                self.sync_changes()
                UI.prompt("\nPress Enter to continue...")
                
            elif choice == '2':
                self.show_detailed_status()
                UI.prompt("\nPress Enter to continue...")
                
            elif choice == '3':
                confirm = UI.prompt("Reset will mark all files as new. Continue? (y/n): ")
                if confirm.lower() == 'y':
                    self.file_hashes = {}
                    self.save_config()
                    UI.success("Tracking reset!")
                    time.sleep(1)
                    
            elif choice == '4':
                self.show_settings()
                UI.prompt("\nPress Enter to continue...")
                
            elif choice == '5':
                self.delete_configuration()
                
            elif choice == '6':
                UI.info("Goodbye!")
                break
                
            else:
                UI.error("Invalid choice!")
                time.sleep(1)
    
    def delete_configuration(self):
        """Delete current configuration"""
        UI.section("Delete Configuration")
        UI.warning(f"This will delete the configuration for: {self.watch_folder}")
        UI.warning("You'll need to set it up again to use it.")
        
        confirm = UI.prompt("\nAre you sure? (type 'yes' to confirm): ")
        if confirm.lower() == 'yes':
            try:
                os.remove(self.config_file)
                UI.success("Configuration deleted!")
                UI.info("Exiting...")
                time.sleep(2)
                sys.exit(0)
            except Exception as e:
                UI.error(f"Failed to delete configuration: {e}")
                time.sleep(2)
        else:
            UI.info("Deletion cancelled.")
            time.sleep(1)
    
    def show_detailed_status(self):
        """Show detailed status"""
        UI.section("Detailed Status")
        
        changes = self.scan_folder(save_changes=False)
        
        if changes['new']:
            print(f"\n{Fore.GREEN}New files ({len(changes['new'])}):{Style.RESET_ALL}")
            for file in changes['new']:
                size = os.path.getsize(os.path.join(self.watch_folder, file))
                size_str = self.format_size(size)
                print(f"  + {file} ({size_str})")
                
        if changes['modified']:
            print(f"\n{Fore.BLUE}Modified files ({len(changes['modified'])}):{Style.RESET_ALL}")
            for file in changes['modified']:
                size = os.path.getsize(os.path.join(self.watch_folder, file))
                size_str = self.format_size(size)
                print(f"  M {file} ({size_str})")
    
    def show_settings(self):
        """Show current settings"""
        UI.section("Current Settings")
        
        print(f"\n{Style.BRIGHT}Local Settings:{Style.RESET_ALL}")
        print(f"  Config file: {self.config_file}")
        print(f"  Tracked files: {len(self.file_hashes)}")
        
        print(f"\n{Style.BRIGHT}FTP Settings:{Style.RESET_ALL}")
        print(f"  Host: {self.ftp_config['host']}")
        print(f"  Port: {self.ftp_config['port']}")
        print(f"  Username: {self.ftp_config['username']}")
        print(f"  Remote path: {self.ftp_config['remote_path']}")
        
        print(f"\n{Style.BRIGHT}Ignored Patterns:{Style.RESET_ALL}")
        for pattern in self.ignore_patterns:
            print(f"  - {pattern}")
    
    def format_size(self, bytes):
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} TB"

def main():
    parser = argparse.ArgumentParser(description='FTP Folder Sync Tool')
    parser.add_argument('folder', nargs='?', help='Folder path to watch and sync')
    parser.add_argument('--list', action='store_true', help='List all saved configurations')
    parser.add_argument('--delete', action='store_true', help='Delete saved configurations')
    args = parser.parse_args()
    
    # Show banner
    if not args.list and not args.delete:
        UI.clear()
        print(f"{Fore.CYAN}")
        print("  _____ _____ ____    ____                  ")
        print(" |  ___|_   _|  _ \\  / ___|_   _ _ __   ___ ")
        print(" | |_    | | | |_) | \\___ \\| | | | '_ \\ / __|")
        print(" |  _|   | | |  __/   ___) | |_| | | | | (__ ")
        print(" |_|     |_| |_|     |____/ \\__, |_| |_|\\___|")
        print("                            |___/            ")
        print(f"{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}        Professional FTP Synchronization Tool{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─' * 50}{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}        Made with {Fore.RED}❤️  {Fore.MAGENTA}and {Fore.YELLOW}⚡ {Fore.MAGENTA}passion{Style.RESET_ALL}")
        print(f"{Fore.BLUE}       github.com/mansourjabin/ftp-sync-tool{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─' * 50}{Style.RESET_ALL}\n")
        time.sleep(1.5)
    
    # List configurations
    if args.list:
        config_dir = os.path.join(os.path.expanduser("~"), ".ftp_sync")
        if os.path.exists(config_dir):
            configs = [f for f in os.listdir(config_dir) if f.endswith('.json')]
            if configs:
                UI.header("Saved Configurations")
                for i, config in enumerate(configs, 1):
                    config_path = os.path.join(config_dir, config)
                    try:
                        with open(config_path, 'r') as f:
                            data = json.load(f)
                            print(f"  {Fore.GREEN}[{i}]{Style.RESET_ALL} {data['watch_folder']} → {data['ftp_config']['host']}")
                    except:
                        pass
            else:
                UI.info("No saved configurations found.")
        return
    
    # Delete configurations
    if args.delete:
        config_dir = os.path.join(os.path.expanduser("~"), ".ftp_sync")
        if os.path.exists(config_dir):
            configs = [f for f in os.listdir(config_dir) if f.endswith('.json')]
            if configs:
                UI.header("Delete Configurations")
                config_list = []
                for i, config in enumerate(configs, 1):
                    config_path = os.path.join(config_dir, config)
                    try:
                        with open(config_path, 'r') as f:
                            data = json.load(f)
                            config_list.append((config_path, data['watch_folder'], data['ftp_config']['host']))
                            print(f"  {Fore.RED}[{i}]{Style.RESET_ALL} {data['watch_folder']} → {data['ftp_config']['host']}")
                    except:
                        pass
                
                print(f"\n  {Fore.YELLOW}[A]{Style.RESET_ALL} Delete all configurations")
                print(f"  {Fore.GREEN}[C]{Style.RESET_ALL} Cancel")
                
                choice = UI.prompt("\nYour choice: ").strip().upper()
                
                if choice == 'C':
                    UI.info("Deletion cancelled.")
                elif choice == 'A':
                    confirm = UI.prompt("Delete ALL configurations? (type 'yes' to confirm): ")
                    if confirm.lower() == 'yes':
                        for config_path, _, _ in config_list:
                            try:
                                os.remove(config_path)
                            except:
                                pass
                        UI.success("All configurations deleted!")
                else:
                    try:
                        index = int(choice) - 1
                        if 0 <= index < len(config_list):
                            config_path, folder, host = config_list[index]
                            confirm = UI.prompt(f"Delete config for {folder}? (y/n): ")
                            if confirm.lower() == 'y':
                                os.remove(config_path)
                                UI.success("Configuration deleted!")
                        else:
                            UI.error("Invalid selection.")
                    except ValueError:
                        UI.error("Invalid choice.")
            else:
                UI.info("No configurations found to delete.")
        return
    
    # Get folder path
    if args.folder:
        watch_folder = os.path.abspath(args.folder)
    else:
        config_dir = os.path.join(os.path.expanduser("~"), ".ftp_sync")
        saved_folders = []
        
        if os.path.exists(config_dir):
            configs = [f for f in os.listdir(config_dir) if f.endswith('.json')]
            for config in configs:
                config_path = os.path.join(config_dir, config)
                try:
                    with open(config_path, 'r') as f:
                        data = json.load(f)
                        saved_folders.append({
                            'path': data['watch_folder'],
                            'host': data['ftp_config']['host']
                        })
                except:
                    pass
        
        if saved_folders:
            UI.section("Select a project")
            for i, folder in enumerate(saved_folders, 1):
                print(f"  {Fore.GREEN}[{i}]{Style.RESET_ALL} {folder['path']}")
                print(f"      {Fore.CYAN}→ {folder['host']}{Style.RESET_ALL}")
            print(f"\n  {Fore.YELLOW}[N]{Style.RESET_ALL} Add new project")
            
            choice = UI.prompt("\nYour choice: ").strip().upper()
            
            if choice == 'N':
                watch_folder = UI.prompt("Enter folder path: ").strip()
                watch_folder = os.path.abspath(watch_folder) if watch_folder else None
            else:
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(saved_folders):
                        watch_folder = saved_folders[index]['path']
                        UI.success(f"Selected: {watch_folder}")
                    else:
                        UI.error("Invalid selection.")
                        return
                except ValueError:
                    UI.error("Invalid choice.")
                    return
        else:
            watch_folder = UI.prompt("Enter folder path to sync: ").strip()
            watch_folder = os.path.abspath(watch_folder) if watch_folder else None
        
        if not watch_folder:
            UI.error("No folder selected.")
            return
    
    # Create watcher
    watcher = FolderWatcher(watch_folder)
    
    # Check for existing configuration
    if watcher.load_config():
        UI.info(f"Configuration found for: {watch_folder}")
        use_existing = UI.prompt("Use existing configuration? (y/n): ")
        if use_existing.lower() != 'y':
            if not watcher.setup():
                return
    else:
        UI.info(f"No configuration found for: {watch_folder}")
        if not watcher.setup():
            return
            
    # Start watching
    watcher.watch()

if __name__ == "__main__":
    main()
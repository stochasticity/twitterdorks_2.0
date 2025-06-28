import datetime
import subprocess
import os
import re
import sys
import shutil
import json
import webbrowser
import time
from pathlib import Path

def get_bundled_path(filename):
    """Get path to bundled file in PyInstaller exe"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return os.path.join(sys._MEIPASS, filename)
    else:
        # Running as script - look in current directory
        return filename

def get_ffmpeg_path():
    """Get path to FFmpeg - bundled or system"""
    # First check for bundled ffmpeg
    bundled_ffmpeg = get_bundled_path("ffmpeg.exe")
    if os.path.exists(bundled_ffmpeg):
        return bundled_ffmpeg
    
    # Then check system
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    
    # If not found, return the filename and hope for the best
    return "ffmpeg"

def get_ytdlp_path():
    """Get path to yt-dlp - bundled or system"""
    # First check for bundled yt-dlp
    bundled_ytdlp = get_bundled_path("yt-dlp.exe")
    if os.path.exists(bundled_ytdlp):
        return bundled_ytdlp
    
    # Then check system
    system_ytdlp = shutil.which("yt-dlp")
    if system_ytdlp:
        return system_ytdlp
    
    # If not found, return the filename
    return "yt-dlp"

class TwitterSpacesDownloader:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.app_dir = Path.home() / "TwitterSpacesDownloader"
        else:
            self.app_dir = Path(__file__).parent
        
        self.app_dir.mkdir(exist_ok=True)
        self.downloads_dir = self.app_dir / "Downloads"
        self.cookies_file = self.app_dir / "cookies.txt"
        self.error_log = self.app_dir / "error.log"
        self.settings_file = self.app_dir / "settings.json"
        
        self.downloads_dir.mkdir(exist_ok=True)
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load user settings"""
        default_settings = {
            "last_login": None,
            "username": "",
            "save_username": False,
            "preferred_format": "m4a",
            "preferred_format_name": "🎶 M4A (Audio Only)"
        }
        
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    default_settings.update(saved_settings)
        except Exception:
            pass
            
        return default_settings
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass
    
    def print_header(self):
        """Print a nice header for the application"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=" * 70)
        print("🎙️         TWITTER SPACES DOWNLOADER         🎙️")
        print("=" * 70)
        print("📁 Downloads folder:", self.downloads_dir)
        print("-" * 70)
    
    def check_dependencies(self):
        """Check if bundled dependencies are available"""
        print("🔍 Checking dependencies...")
        
        # Check yt-dlp
        ytdlp_path = get_ytdlp_path()
        if os.path.exists(ytdlp_path):
            print("✅ yt-dlp found")
        else:
            print("❌ yt-dlp not found - downloads may fail")
            return False
        
        # Check FFmpeg
        ffmpeg_path = get_ffmpeg_path()
        if os.path.exists(ffmpeg_path):
            print("✅ FFmpeg found")
        else:
            print("⚠️  FFmpeg not found - audio conversion may fail")
        
        print("✅ Dependencies check complete!")
        return True
    
    def validate_cookies(self):
        """Check if cookies file exists and contains auth_token"""
        try:
            if not self.cookies_file.exists():
                return False
                
            with open(self.cookies_file, "r", encoding='utf-8') as f:
                content = f.read()
                
            if not ("auth_token" in content and "x.com" in content):
                return False
            
            print("✅ Valid authentication found.")
            return True
            
        except Exception:
            return False
    
    def manual_cookie_setup(self):
        """Manual cookie extraction method - 100% reliable"""
        print("\\n" + "=" * 70)
        print("🍪 AUTHENTICATION SETUP")
        print("=" * 70)
        print("We'll use a simple manual method that works 100% of the time!")
        print("This is actually MORE reliable than automated login.")
        print()
        print("📋 SIMPLE 3-STEP PROCESS:")
        print()
        print("1️⃣  I'll open Twitter in your browser")
        print("2️⃣  You login normally (like you always do)")
        print("3️⃣  You copy 2 values and paste them here")
        print()
        print("⏱️  Takes 30 seconds, works perfectly every time!")
        print()
        
        proceed = input("🚀 Ready to start? (y/n): ").lower().strip()
        if proceed != 'y':
            return False
        
        print("\\n🌐 Opening Twitter in your browser...")
        try:
            webbrowser.open("https://x.com")
            print("✅ Browser opened with Twitter")
        except:
            print("❌ Could not open browser automatically")
            print("💡 Please manually go to https://x.com")
        
        print("\\n" + "=" * 70)
        print("📋 STEP-BY-STEP INSTRUCTIONS:")
        print("=" * 70)
        print("1. Login to Twitter in the browser")
        print("2. After logging in, press F12 (opens Developer Tools)")
        print("3. Click the 'Application' tab (or 'Storage' in Firefox)")
        print("4. On the left, click 'Cookies' → 'https://x.com'")
        print("5. Find the cookie named 'auth_token'")
        print("6. Copy the VALUE (long string of letters/numbers)")
        print()
        print("💡 TIP: Double-click the value to select it all, then Ctrl+C")
        print()
        
        input("✅ Press Enter when you've completed steps 1-6...")
        
        print("\\n🔑 Paste the auth_token value here:")
        auth_token = input("auth_token: ").strip()
        
        if not auth_token or len(auth_token) < 20:
            print("❌ auth_token seems invalid (too short or empty)")
            return False
        
        print("\\n7. Now find the cookie named 'ct0'")
        print("8. Copy its VALUE (another long string)")
        ct0_token = input("\\nct0: ").strip()
        
        if not ct0_token or len(ct0_token) < 20:
            print("❌ ct0 token seems invalid (too short or empty)")
            return False
        
        current_time = int(time.time())
        expiry_time = current_time + (86400 * 30)
        
        cookies_content = f"""# Netscape HTTP Cookie File
# Generated by Twitter Spaces Downloader
# Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

.x.com	TRUE	/	TRUE	{expiry_time}	auth_token	{auth_token}
.x.com	TRUE	/	FALSE	{expiry_time}	ct0	{ct0_token}
.x.com	TRUE	/	FALSE	{expiry_time}	guest_id	v1%3A{current_time}
"""
        
        try:
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                f.write(cookies_content)
            
            print("\\n✅ Authentication saved successfully!")
            print(f"💾 Cookies saved to: {self.cookies_file}")
            print("⏰ Valid for 30 days - no need to repeat this process!")
            print("🎉 You're all set!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save cookies: {e}")
            return False
    
    def validate_space_url(self, url):
        """Validate Twitter Space URL format - supports multiple formats"""
        # Clean the URL first
        url = url.strip()
        
        # Remove any query parameters or fragments for validation
        url_clean = url.split('?')[0].split('#')[0]
        
        patterns = [
            r'https://x\.com/i/spaces/[a-zA-Z0-9_-]+',
            r'https://twitter\.com/i/spaces/[a-zA-Z0-9_-]+',
            r'https://x\.com/i/broadcasts/[a-zA-Z0-9_-]+',
            r'https://twitter\.com/i/broadcasts/[a-zA-Z0-9_-]+',
            r'https://x\.com/[^/]+/status/[0-9]+',
            r'https://twitter\.com/[^/]+/status/[0-9]+'
        ]
        
        # Use search instead of match to be more flexible
        for pattern in patterns:
            if re.search(pattern, url_clean):
                return True
        
        return False
    
    def normalize_space_url(self, url):
        """Normalize different URL formats to work with yt-dlp"""
        url = url.replace("twitter.com", "x.com")
        return url
    
    def get_format_choice(self):
        """Let user choose download format with smart defaults"""
        print("\\n" + "=" * 70)
        print("🎵 CHOOSE DOWNLOAD FORMAT")
        print("=" * 70)
        
        # Get last used format or default to m4a
        preferred = self.settings.get("preferred_format", "m4a")
        preferred_name = self.settings.get("preferred_format_name", "🎶 M4A (Audio Only)")
        
        print("1. 🎥 MP4 - Audio in MP4 container (video if available)")
        print("2. 🎵 MP3 - Universal audio format")
        print("3. 🎶 M4A - Better audio quality than MP3 [DEFAULT]")
        print("4. 🔊 OPUS - Best compression, smallest files")
        print()
        print("📌 Note: Most Twitter Spaces are audio-only broadcasts")
        print(f"📌 Last used: {preferred_name}")
        print("💡 Press Enter for default (M4A) or last used format")
        
        format_options = {
            "1": ("mp4", "🎥 MP4 Container"),
            "2": ("mp3", "🎵 MP3 (Audio Only)"),
            "3": ("m4a", "🎶 M4A (Audio Only)"),
            "4": ("opus", "🔊 OPUS (Audio Only)"),
            "": (preferred, preferred_name)  # Empty string = Enter pressed
        }
        
        choice = input("\\n👉 Choose format (1-4) [Enter = last used]: ").strip()
        
        if choice in format_options:
            format_ext, format_name = format_options[choice]
            
            # Always save the choice as preferred (no asking)
            if choice != "":  # Only update if user made an actual choice
                self.settings["preferred_format"] = format_ext
                self.settings["preferred_format_name"] = format_name
                self.save_settings()
            
            return format_ext, format_name
        else:
            # Invalid choice, use default
            print(f"⚡ Using last format: {preferred_name}")
            return preferred, preferred_name
    
    def download_twitter_space(self, url, format_ext="m4a"):
        """Download Twitter Space using yt-dlp with format selection and CC support"""
        if not self.validate_space_url(url):
            print("❌ Invalid Twitter Space/Broadcast URL format")
            return False

        normalized_url = self.normalize_space_url(url)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determine output format and settings
        if format_ext == "mp4":
            # For MP4, we want video if available, but will accept audio-only in MP4 container
            output_format = str(self.downloads_dir / f"space_{timestamp}_%(uploader)s_%(upload_date)s_%(id)s.mp4")
            # Try to get video first, fall back to audio wrapped in MP4
            format_selector = "best[ext=mp4]/bestvideo+bestaudio/best"
        else:
            output_format = str(self.downloads_dir / f"space_{timestamp}_%(uploader)s_%(upload_date)s_%(id)s.{format_ext}")
            format_selector = "bestaudio/best"

        ytdlp_path = get_ytdlp_path()
        ffmpeg_path = get_ffmpeg_path()

        command = [
            ytdlp_path,
            "--cookies", str(self.cookies_file),
            "--no-clean-info-json",
            "--write-comments",
            "--write-subs",          # Download subtitles
            "--write-auto-subs",     # Download auto-generated subtitles
            "--sub-langs", "all",    # Download all available subtitle languages
            "--convert-subs", "srt", # Convert to SRT format
            "--ffmpeg-location", ffmpeg_path,
            "--no-warnings"
        ]
        
        if format_ext == "mp4":
            # For MP4, we want to keep video if available, or remux audio to MP4 container
            command.extend([
                "--remux-video", "mp4",  # Ensure MP4 container even for audio-only
                "--embed-subs",          # Embed subtitles in video
                "--merge-output-format", "mp4"  # Force MP4 output
            ])
        else:
            # For audio formats, extract audio
            command.extend(["--extract-audio"])
            if format_ext == "mp3":
                command.extend(["--audio-format", "mp3"])
            elif format_ext == "m4a":
                command.extend(["--audio-format", "m4a"])
            elif format_ext == "opus":
                command.extend(["--audio-format", "opus"])
        
        command.extend([
            "-f", format_selector,
            normalized_url,
            "-o", output_format
        ])

        print(f"\\n⬇️  Starting download...")
        print(f"🎯 URL: {normalized_url}")
        print(f"🎵 Format: {format_ext.upper()}")
        print(f"📁 Saving to: {self.downloads_dir}")
        if format_ext == "mp4":
            print("📹 Note: Most Spaces are audio-only. MP4 will contain audio in MP4 container.")
        print("📝 Closed captions will be saved if available")
        print("⏰ No time limit - will download entire Space!")
        print("🛑 Press Ctrl+C to cancel download if needed")
        print("\\n🔄 Download in progress...")

        try:
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            result_code = process.returncode
            
            if result_code == 0:
                print("\\n✅ Download completed successfully!")
                
                # Look for downloaded files
                downloaded_files = list(self.downloads_dir.glob(f"space_{timestamp}_*"))
                if downloaded_files:
                    main_file = None
                    for f in downloaded_files:
                        if f.suffix.lower() in ['.mp4', '.m4a', '.mp3', '.opus']:
                            main_file = f
                            break
                    
                    if main_file:
                        file_size = main_file.stat().st_size / (1024 * 1024)
                        print(f"📄 File: {main_file.name}")
                        print(f"📊 Size: {file_size:.1f} MB")
                        
                        # Note about MP4 audio-only
                        if format_ext == "mp4" and file_size < 50:  # Small MP4 likely audio-only
                            print("📹 Note: This Space was audio-only, saved as MP4 container with audio")
                        
                        # Check for subtitle files
                        subtitle_files = list(self.downloads_dir.glob(f"space_{timestamp}_*.srt"))
                        if subtitle_files:
                            print(f"📝 Closed captions saved: {len(subtitle_files)} file(s)")
                            for sub_file in subtitle_files:
                                print(f"   • {sub_file.name}")
                
                return True
            else:
                print("\\n❌ Download failed!")
                
                error_output = stderr.lower()
                if "ffmpeg" in error_output:
                    print("💡 FFmpeg issue detected. FFmpeg may not be properly bundled.")
                elif "auth" in error_output or "forbidden" in error_output:
                    print("💡 Authentication issue - your cookies may have expired.")
                    print("💡 Try refreshing authentication (option in main menu).")
                elif "not found" in error_output or "unavailable" in error_output:
                    print("💡 Space not found or no longer available.")
                elif "private" in error_output:
                    print("💡 This appears to be a private Space.")
                elif "format" in error_output:
                    print(f"💡 The requested {format_ext.upper()} format may not be available.")
                    print("💡 Try a different format option.")
                else:
                    print("💡 Check the error log for details.")
                
                with open(self.error_log, "w", encoding='utf-8') as log_file:
                    log_file.write(f"Error Log - {datetime.datetime.now()}\\n")
                    log_file.write("=" * 50 + "\\n")
                    log_file.write(f"URL: {url}\\n")
                    log_file.write(f"Format: {format_ext}\\n")
                    log_file.write(f"Command: {' '.join(command)}\\n\\n")
                    log_file.write("STDOUT:\\n")
                    log_file.write(stdout + "\\n\\n")
                    log_file.write("STDERR:\\n")
                    log_file.write(stderr)
                
                return False
                
        except KeyboardInterrupt:
            print("\\n❌ Download cancelled by user (Ctrl+C)")
            print("💡 The partial download may be saved to your downloads folder")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def get_space_url(self):
        """Get and validate Space URL with helpful hints"""
        print("\\n" + "=" * 70)
        print("🎙️  TWITTER SPACE TO DOWNLOAD")
        print("=" * 70)
        print("💡 Supported URL formats:")
        print("   • https://x.com/i/spaces/1YpKklAePYBGj")
        print("   • https://x.com/i/broadcasts/1BRJjPaVvNwsw")
        print("   • https://x.com/username/status/1234567890")
        print("   • https://twitter.com/... (old format)")
        print()
        print("📋 How to find the URL:")
        print("   1. Go to Twitter and find the Space/Broadcast")
        print("   2. Click on the Space or tweet containing it")
        print("   3. Copy the URL from your browser's address bar")
        
        while True:
            url = input("\\n🔗 Enter Twitter Space URL: ").strip()
            if not url:
                print("❌ URL cannot be empty.")
                continue
                
            if self.validate_space_url(url):
                return url
            else:
                print("❌ Invalid URL format.")
                print("💡 Supported formats:")
                print("   • https://x.com/i/spaces/[SPACE_ID]")
                print("   • https://x.com/i/broadcasts/[BROADCAST_ID]") 
                print("   • https://x.com/username/status/[TWEET_ID]")
                print("   • https://twitter.com/... (old format)")
                print("💡 Make sure to use the complete URL from your browser")
    
    def run(self):
        """Main application"""
        try:
            self.print_header()
            
            print("🚀 Starting Twitter Spaces Downloader...")
            print("✨ Standalone version - no Python required!")
            
            if not self.check_dependencies():
                print("\\n⚠️  Some dependencies are missing.")
                print("💡 This standalone version should include all dependencies.")
                input("Press Enter to continue anyway, or Ctrl+C to exit...")
            
            while True:
                if not self.validate_cookies():
                    print("\\n🔑 Authentication required...")
                    if not self.manual_cookie_setup():
                        print("❌ Authentication setup cancelled.")
                        break
                
                print("\\n🎉 Ready to download Twitter Spaces!")
                print("\\n" + "=" * 70)
                print("📋 MAIN MENU")
                print("=" * 70)
                print("1. Download a Twitter Space [DEFAULT]")
                print("2. Refresh authentication")
                print("3. Open downloads folder")
                print("4. Exit")
                print()
                print("💡 Press Enter to download a Space")
                
                choice = input("\\n👉 Choose an option (1-4) [Enter = 1]: ").strip()
                
                # Default to option 1 if Enter pressed
                if choice == "":
                    choice = "1"
                
                if choice == "1":
                    try:
                        space_url = self.get_space_url()
                        format_ext, format_name = self.get_format_choice()
                        
                        print(f"\\n📋 Ready to download:")
                        print(f"   🔗 URL: {space_url}")
                        print(f"   🎵 Format: {format_name}")
                        print(f"   📁 Folder: {self.downloads_dir}")
                        print()
                        print("⚠️  IMPORTANT FOR LONG SPACES:")
                        print("   • This app can handle 12+ hour recordings")
                        print("   • No timeout limits - will download complete Space")
                        print("   • For live Spaces, download continues until Space ends")
                        print("   • Keep this window open during download")
                        print("   • Use Ctrl+C to cancel if needed")
                        
                        confirm = input("\\n▶️  Start download? (Y/n) [Enter = Yes]: ").lower().strip()
                        if confirm == '' or confirm == 'y':
                            success = self.download_twitter_space(space_url, format_ext)
                            
                            if success:
                                print("\\n🎉 Download completed successfully!")
                                print(f"📂 Check your files: {self.downloads_dir}")
                            else:
                                print("\\n❌ Download failed. Check error details above.")
                        else:
                            print("❌ Download cancelled.")
                            
                    except KeyboardInterrupt:
                        print("\\n👋 Cancelled.")
                
                elif choice == "2":
                    print("\\n🔄 Refreshing authentication...")
                    if self.manual_cookie_setup():
                        print("✅ Authentication refreshed successfully!")
                    else:
                        print("❌ Authentication refresh cancelled.")
                
                elif choice == "3":
                    try:
                        os.startfile(self.downloads_dir)
                        print(f"📂 Opened downloads folder: {self.downloads_dir}")
                    except:
                        print(f"📁 Downloads folder: {self.downloads_dir}")
                
                elif choice == "4":
                    print("\\n👋 Thanks for using Twitter Spaces Downloader!")
                    break
                
                else:
                    print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
                
                input("\\nPress Enter to continue...")
            
            if getattr(sys, 'frozen', False):
                input("\\nPress Enter to exit...")
            
        except KeyboardInterrupt:
            print("\\n\\n👋 Goodbye!")
        except Exception as e:
            print(f"\\n❌ Unexpected error: {e}")
            if getattr(sys, 'frozen', False):
                input("Press Enter to exit...")

def main():
    downloader = TwitterSpacesDownloader()
    downloader.run()

if __name__ == "__main__":
    main()
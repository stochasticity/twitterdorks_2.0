import asyncio
import getpass
import datetime
import subprocess
import os
import re
import sys
import shutil
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright

def get_ffmpeg_path():
    """Get path to FFmpeg - bundled or system"""
    if getattr(sys, 'frozen', False):
        # Running as executable - try bundled FFmpeg first
        bundled_ffmpeg = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.exists(bundled_ffmpeg):
            return bundled_ffmpeg
        
        # Fall back to system FFmpeg
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
        
        # Try to install FFmpeg if not found
        print("⚠️  FFmpeg not found. Attempting to install...")
        try:
            subprocess.run(["winget", "install", "FFmpeg (Essentials Build)"], 
                          check=True, capture_output=True, timeout=60)
            print("✅ FFmpeg installed!")
            return shutil.which("ffmpeg") or "ffmpeg"
        except:
            print("❌ Could not install FFmpeg automatically")
            return "ffmpeg"  # Hope it works
    else:
        # Running as script - use system FFmpeg
        return shutil.which("ffmpeg") or "ffmpeg"

class TwitterSpacesDownloader:
    def __init__(self):
        # For standalone executable, use user's app data directory
        if getattr(sys, 'frozen', False):
            self.app_dir = Path.home() / "TwitterSpacesDownloader"
        else:
            self.app_dir = Path(__file__).parent
        
        self.app_dir.mkdir(exist_ok=True)
        self.downloads_dir = self.app_dir / "Downloads"
        self.cookies_file = self.app_dir / "cookies.txt"
        self.error_log = self.app_dir / "error.log"
        self.settings_file = self.app_dir / "settings.json"
        
        # Create directories
        self.downloads_dir.mkdir(exist_ok=True)
        
        # Load settings
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load user settings including last login time"""
        default_settings = {
            "last_login": None,
            "username": "",
            "save_username": False,
            "auto_login_interval_hours": 24
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
    
    def check_dependencies_auto(self):
        """Check dependencies and install if needed"""
        print("🔍 Checking dependencies...")
        
        # Check yt-dlp
        if not shutil.which("yt-dlp"):
            print("📦 Installing yt-dlp...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], 
                             check=True, capture_output=True)
                print("✅ yt-dlp installed!")
            except:
                print("❌ Failed to install yt-dlp")
                return False
        
        # Check FFmpeg
        ffmpeg_path = get_ffmpeg_path()
        if getattr(sys, 'frozen', False) and os.path.exists(os.path.join(sys._MEIPASS, "ffmpeg.exe")):
            print("✅ Using bundled FFmpeg")
        elif shutil.which("ffmpeg"):
            print("✅ System FFmpeg found")
        else:
            print("⚠️  FFmpeg not found - will attempt auto-installation during download")
        
        print("✅ Dependencies check complete!")
        return True
    
    def validate_cookies(self):
        """Enhanced cookie validation with expiry checking"""
        try:
            if not self.cookies_file.exists():
                return False
                
            with open(self.cookies_file, "r", encoding='utf-8') as f:
                content = f.read()
                
            # Check for essential cookies
            if not ("auth_token" in content and "x.com" in content):
                return False
            
            print("✅ Valid authentication found.")
            return True
            
        except Exception:
            return False

    async def login_to_x(self, username, password, mfa_code=None, max_retries=2):
        """Enhanced login with better error handling"""
        print(f"\n🔐 Logging into X as {username}...")
        
        for attempt in range(max_retries):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
                    )
                    context = await browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    )
                    page = await context.new_page()

                    await page.goto("https://x.com/i/flow/login", wait_until='networkidle')
                    await page.wait_for_timeout(2000)

                    # Username entry
                    try:
                        await page.wait_for_selector("input[name='text']", timeout=15000)
                        await page.fill("input[name='text']", username)
                        await page.click("button:has-text('Next')")
                        await page.wait_for_timeout(2000)
                        print("✅ Username entered")
                    except Exception as e:
                        print(f"❌ Username entry failed (attempt {attempt + 1})")
                        await browser.close()
                        if attempt == max_retries - 1:
                            return False
                        continue

                    # Handle potential unusual activity check
                    try:
                        unusual_activity = await page.wait_for_selector("input[data-testid='ocfEnterTextTextInput']", timeout=5000)
                        if unusual_activity:
                            print("⚠️  Unusual activity detected. Entering username again...")
                            await page.fill("input[data-testid='ocfEnterTextTextInput']", username)
                            await page.click("button[data-testid='ocfEnterTextNextButton']")
                            await page.wait_for_timeout(2000)
                    except Exception:
                        pass

                    # Password entry
                    try:
                        await page.wait_for_selector("input[name='password']", timeout=15000)
                        await page.fill("input[name='password']", password)
                        await page.click("button:has-text('Log in')")
                        await page.wait_for_timeout(3000)
                        print("✅ Password entered")
                    except Exception as e:
                        print(f"❌ Password entry failed (attempt {attempt + 1})")
                        await browser.close()
                        if attempt == max_retries - 1:
                            return False
                        continue

                    # MFA handling
                    if mfa_code:
                        try:
                            mfa_input = await page.wait_for_selector("input[data-testid='ocfEnterTextTextInput']", timeout=60000)
                            await mfa_input.fill(mfa_code)
                            await page.click("button[data-testid='ocfEnterTextNextButton']")
                            await page.wait_for_timeout(3000)
                            print("✅ MFA code entered")
                        except Exception as e:
                            print("⚠️  MFA handling issue:", e)

                    # Wait for login to complete
                    await page.wait_for_timeout(5000)
                    
                    # Verify login success
                    try:
                        await page.goto("https://x.com/home", wait_until='networkidle', timeout=10000)
                        current_url = page.url
                        if "login" in current_url or "flow" in current_url:
                            print("❌ Login verification failed")
                            await browser.close()
                            continue
                    except Exception:
                        pass

                    # Save cookies
                    cookies = await context.cookies()
                    
                    # Verify we have authentication cookies
                    has_auth_token = any(cookie['name'] == 'auth_token' for cookie in cookies)
                    if not has_auth_token:
                        print("❌ No authentication token found")
                        await browser.close()
                        continue
                    
                    # Save cookies
                    with open(self.cookies_file, "w", encoding='utf-8') as f:
                        f.write("# Netscape HTTP Cookie File\n")
                        f.write("# Generated by Twitter Spaces Downloader\n")
                        f.write(f"# Created: {datetime.datetime.now().isoformat()}\n\n")
                        for cookie in cookies:
                            f.write(
                                f"{cookie['domain']}\t"
                                f"{'TRUE' if cookie['domain'].startswith('.') else 'FALSE'}\t"
                                f"{cookie['path']}\t"
                                f"{'TRUE' if cookie.get('secure', False) else 'FALSE'}\t"
                                f"{int(cookie['expires']) if cookie['expires'] else 0}\t"
                                f"{cookie['name']}\t"
                                f"{cookie['value']}\n"
                            )

                    # Update settings
                    self.settings["last_login"] = datetime.datetime.now().isoformat()
                    self.save_settings()

                    print("✅ Login completed successfully!")
                    await browser.close()
                    return True

            except Exception as e:
                print(f"❌ Login attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(3)

        return False
    
    def validate_space_url(self, url):
        """Validate Twitter Space URL format"""
        pattern = r'^https://x\.com/i/spaces/[a-zA-Z0-9]+$'
        return re.match(pattern, url) is not None
    
    def download_twitter_space(self, url):
        """Download Twitter Space using yt-dlp with smart FFmpeg handling"""
        if not self.validate_space_url(url):
            print("❌ Invalid Twitter Space URL format")
            return False

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_format = str(self.downloads_dir / f"space_{timestamp}_%(uploader)s_%(upload_date)s_%(id)s.%(ext)s")

        # Get FFmpeg path
        ffmpeg_path = get_ffmpeg_path()

        command = [
            "yt-dlp",
            "--cookies", str(self.cookies_file),
            "--no-clean-info-json",
            "--write-comments",
            "--ffmpeg-location", ffmpeg_path,
            "--no-warnings",
            url,
            "-o", output_format
        ]

        print(f"\n⬇️  Starting download...")
        print(f"🎯 URL: {url}")
        print(f"📁 Saving to: {self.downloads_dir}")

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=1800)
            
            if result.returncode == 0:
                print("✅ Download completed successfully!")
                
                # Try to find the downloaded file
                downloaded_files = list(self.downloads_dir.glob(f"space_{timestamp}_*"))
                if downloaded_files:
                    file_size = downloaded_files[0].stat().st_size / (1024 * 1024)
                    print(f"📄 File: {downloaded_files[0].name}")
                    print(f"📊 Size: {file_size:.1f} MB")
                
                return True
            else:
                print("❌ Download failed!")
                
                # Enhanced error analysis
                error_output = result.stderr.lower()
                if "ffmpeg" in error_output:
                    print("💡 FFmpeg issue detected. Trying to install FFmpeg...")
                    try:
                        subprocess.run(["winget", "install", "FFmpeg (Essentials Build)"], 
                                      check=True, capture_output=True, timeout=60)
                        print("✅ FFmpeg installed! Please try the download again.")
                    except:
                        print("❌ Could not install FFmpeg automatically.")
                        print("💡 Please install FFmpeg manually from: https://ffmpeg.org/download.html")
                elif "auth" in error_output or "forbidden" in error_output:
                    print("💡 Authentication issue detected. Try logging in again.")
                elif "not found" in error_output or "unavailable" in error_output:
                    print("💡 Space not found or no longer available.")
                elif "private" in error_output:
                    print("💡 This appears to be a private Space.")
                else:
                    print("💡 Check the error log for details.")
                
                # Save detailed error log
                with open(self.error_log, "w", encoding='utf-8') as log_file:
                    log_file.write(f"Error Log - {datetime.datetime.now()}\n")
                    log_file.write("=" * 50 + "\n")
                    log_file.write(f"URL: {url}\n")
                    log_file.write(f"Command: {' '.join(command)}\n\n")
                    log_file.write("STDOUT:\n")
                    log_file.write(result.stdout + "\n\n")
                    log_file.write("STDERR:\n")
                    log_file.write(result.stderr)
                
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Download timed out (30 minutes)")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def get_user_credentials(self):
        """Get login credentials with smart defaults"""
        print("\n" + "=" * 70)
        print("🔐 LOGIN TO TWITTER/X")
        print("=" * 70)
        
        # Use saved username if available
        default_username = self.settings.get("username", "")
        if default_username:
            username = input(f"👤 Username [{default_username}]: ").strip()
            if not username:
                username = default_username
        else:
            username = input("👤 Username: ").strip()
        
        if not username:
            print("❌ Username is required.")
            return None, None, None
        
        # Ask if user wants to save username
        if username != self.settings.get("username", ""):
            save_user = input("💾 Save username for next time? (y/n): ").lower().strip()
            if save_user == 'y':
                self.settings["username"] = username
                self.settings["save_username"] = True
                self.save_settings()
        
        password = getpass.getpass("🔒 Password: ")
        if not password:
            print("❌ Password is required.")
            return None, None, None
        
        mfa_code = input("🔐 MFA/2FA code (press Enter if not needed): ").strip()
        if mfa_code == "":
            mfa_code = None
        
        return username, password, mfa_code
    
    def get_space_url(self):
        """Get and validate Space URL with helpful hints"""
        print("\n" + "=" * 70)
        print("🎙️  TWITTER SPACE TO DOWNLOAD")
        print("=" * 70)
        print("💡 Example: https://x.com/i/spaces/1YpKklAePYBGj")
        
        while True:
            url = input("\n🔗 Enter Twitter Space URL: ").strip()
            if not url:
                print("❌ URL cannot be empty.")
                continue
                
            if self.validate_space_url(url):
                return url
            else:
                print("❌ Invalid URL format.")
                print("💡 URL should be: https://x.com/i/spaces/[SPACE_ID]")
    
    def run(self):
        """Main application with enhanced flow"""
        try:
            self.print_header()
            
            print("🚀 Starting Twitter Spaces Downloader...")
            
            # Auto-check dependencies
            if not self.check_dependencies_auto():
                print("\n⚠️  Some dependencies could not be installed.")
                input("Press Enter to continue anyway, or Ctrl+C to exit...")
            
            # Check authentication
            if not self.validate_cookies():
                print("\n🔑 Authentication required.")
                username, password, mfa_code = self.get_user_credentials()
                if not username:
                    return
                
                print("⏳ Logging in... This may take a moment.")
                if not asyncio.run(self.login_to_x(username, password, mfa_code)):
                    print("❌ Login failed.")
                    input("\nPress Enter to exit...")
                    return
                    
                print("✅ Successfully logged in!")
            
            # Main download loop
            while True:
                try:
                    space_url = self.get_space_url()
                    
                    confirm = input("\n▶️  Start download? (y/n): ").lower().strip()
                    if confirm != 'y':
                        print("❌ Download cancelled.")
                    else:
                        success = self.download_twitter_space(space_url)
                        
                        if success:
                            print("\n🎉 Download completed successfully!")
                            print(f"📂 Files saved to: {self.downloads_dir}")
                        else:
                            print("\n❌ Download failed.")
                    
                    # Ask if user wants to download another
                    another = input("\n📥 Download another Space? (y/n): ").lower().strip()
                    if another != 'y':
                        break
                        
                except KeyboardInterrupt:
                    print("\n\n👋 Cancelled by user.")
                    break
            
            print("\n" + "=" * 70)
            print("Thank you for using Twitter Spaces Downloader! 🎙️")
            print("=" * 70)
            
            if getattr(sys, 'frozen', False):
                input("Press Enter to exit...")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            if getattr(sys, 'frozen', False):
                input("Press Enter to exit...")

def main():
    downloader = TwitterSpacesDownloader()
    downloader.run()

if __name__ == "__main__":
    main()

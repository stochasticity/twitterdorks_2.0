import asyncio
import getpass
import datetime
import subprocess
import os
import re
import sys
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

class TwitterSpacesDownloader:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.downloads_dir = self.script_dir / "Downloads"
        self.cookies_file = self.script_dir / "cookies.txt"
        self.error_log = self.script_dir / "yt_dlp_error.log"
        
        # Create Downloads directory if it doesn't exist
        self.downloads_dir.mkdir(exist_ok=True)
        
    def print_header(self):
        """Print a nice header for the application"""
        print("=" * 60)
        print("🎙️  TWITTER SPACES DOWNLOADER  🎙️")
        print("=" * 60)
        print("📁 Downloads will be saved to:", self.downloads_dir)
        print("-" * 60)
    
    def check_dependencies(self):
        """Check and install required dependencies"""
        print("🔍 Checking dependencies...")
        
        missing_deps = []
        
        # Check yt-dlp
        if not self.check_command("yt-dlp"):
            missing_deps.append("yt-dlp")
        
        # Check ffmpeg
        if not self.check_command("ffmpeg"):
            missing_deps.append("ffmpeg")
            
        if missing_deps:
            print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
            if self.prompt_install_dependencies(missing_deps):
                self.install_dependencies(missing_deps)
            else:
                print("❌ Cannot proceed without required dependencies.")
                return False
        else:
            print("✅ All dependencies are installed!")
        
        return True
    
    def check_command(self, command):
        """Check if a command is available in PATH"""
        return shutil.which(command) is not None
    
    def prompt_install_dependencies(self, missing_deps):
        """Ask user if they want to install missing dependencies"""
        print("\n📦 The following dependencies need to be installed:")
        for dep in missing_deps:
            print(f"   • {dep}")
        
        while True:
            response = input("\n❓ Would you like to install them automatically? (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    def install_dependencies(self, missing_deps):
        """Install missing dependencies"""
        print("\n📦 Installing dependencies...")
        
        for dep in missing_deps:
            print(f"\n🔄 Installing {dep}...")
            try:
                if dep == "yt-dlp":
                    subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], 
                                 check=True, capture_output=True)
                    print("✅ yt-dlp installed successfully!")
                    
                elif dep == "ffmpeg":
                    if sys.platform == "win32":
                        # Try winget first
                        try:
                            subprocess.run(["winget", "install", "FFmpeg (Essentials Build)"], 
                                         check=True, capture_output=True)
                            print("✅ ffmpeg installed successfully via winget!")
                            print("⚠️  Please restart this application for PATH changes to take effect.")
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            print("❌ Could not install ffmpeg automatically.")
                            print("💡 Please install manually from: https://www.gyan.dev/ffmpeg/builds/")
                    else:
                        print("❌ Please install ffmpeg manually for your platform.")
                        
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {dep}: {e}")
                return False
                
        return True
    
    def validate_space_url(self, url):
        """Validate Twitter Space URL format"""
        pattern = r'^https://x\.com/i/spaces/[a-zA-Z0-9]+$'
        return re.match(pattern, url) is not None
    
    def sanitize_filename_timestamp(self, timestamp):
        """Ensure timestamp is safe for filename use"""
        return re.sub(r'[^\w\-_.]', '_', timestamp)
    
    async def login_to_x(self, username, password, mfa_code=None, max_retries=3):
        """Login to X with retry logic"""
        print(f"\n🔐 Logging into X as {username}...")
        
        for attempt in range(max_retries):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context()
                    page = await context.new_page()

                    await page.goto("https://x.com/i/flow/login")

                    # Username entry
                    try:
                        await page.wait_for_selector("input[name='text']", timeout=20000)
                        await page.fill("input[name='text']", username)
                        await page.click("button:has-text('Next')")
                        print("✅ Username entered")
                    except Exception as e:
                        print(f"❌ Error entering username (attempt {attempt + 1}): {e}")
                        await browser.close()
                        if attempt == max_retries - 1:
                            return False
                        continue

                    # Password entry
                    try:
                        await page.wait_for_selector("input[name='password']", timeout=20000)
                        await page.fill("input[name='password']", password)
                        await page.click("button:has-text('Log in')")
                        print("✅ Password entered")
                    except Exception as e:
                        print(f"❌ Error entering password (attempt {attempt + 1}): {e}")
                        await browser.close()
                        if attempt == max_retries - 1:
                            return False
                        continue

                    # MFA handling
                    if mfa_code:
                        try:
                            mfa_input = await page.wait_for_selector("input[data-testid='ocfEnterTextTextInput']", timeout=120000)
                            await mfa_input.fill(mfa_code)
                            await page.click("button[data-testid='ocfEnterTextNextButton']")
                            print("✅ MFA code entered")
                        except Exception as e:
                            print("⚠️  No MFA prompt detected or error occurred:", e)

                    # Wait for login completion
                    await page.wait_for_timeout(5000)

                    # Save cookies
                    cookies = await context.cookies()
                    with open(self.cookies_file, "w") as f:
                        f.write("# Netscape HTTP Cookie File\n")
                        f.write("# This file is generated by the spaces downloader script.\n\n")
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

                    print("✅ Login completed! Cookies saved.")
                    await browser.close()
                    return True

            except Exception as e:
                print(f"❌ Unexpected error during login attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(2)

        return False
    
    def validate_cookies(self):
        """Check if cookies file exists and contains auth_token"""
        try:
            with open(self.cookies_file, "r") as f:
                content = f.read()
                if "auth_token" in content and "x.com" in content:
                    print("✅ Valid cookies found. Skipping login.")
                    return True
                else:
                    print("⚠️  Invalid or incomplete cookies. Login required.")
                    return False
        except FileNotFoundError:
            print("⚠️  No cookies file found. Login required.")
            return False
    
    def download_twitter_space(self, url):
        """Download Twitter Space using yt-dlp"""
        if not self.validate_space_url(url):
            print("❌ Invalid Twitter Space URL format")
            return False

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_timestamp = self.sanitize_filename_timestamp(timestamp)
        
        # Output to Downloads subdirectory
        output_format = str(self.downloads_dir / f"twitter_space_{safe_timestamp}_%(uploader)s_%(upload_date)s_%(id)s.%(ext)s")

        command = [
            "yt-dlp",
            "--verbose",
            "--cookies", str(self.cookies_file),
            "--no-clean-info-json",
            "--write-comments",
            url,
            "-o", output_format
        ]

        print(f"\n⬇️  Starting download...")
        print(f"🎯 Target: {url}")

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=3600)
            if result.returncode == 0:
                print("✅ Download successful!")
                print(f"📁 File saved to: {self.downloads_dir}")
                
                # Try to find the downloaded file
                downloaded_files = list(self.downloads_dir.glob(f"twitter_space_{safe_timestamp}_*"))
                if downloaded_files:
                    print(f"📄 Filename: {downloaded_files[0].name}")
                
                return True
            else:
                print("❌ Download failed!")
                print(f"Error code: {result.returncode}")
                
                # Enhanced error logging
                with open(self.error_log, "w") as log_file:
                    log_file.write("YT-DLP Debug Information\n")
                    log_file.write(f"Timestamp: {datetime.datetime.now()}\n")
                    log_file.write("Command:\n")
                    log_file.write(' '.join(command) + "\n\n")
                    log_file.write("STDOUT:\n")
                    log_file.write(result.stdout + "\n\n")
                    log_file.write("STDERR:\n")
                    log_file.write(result.stderr)
                
                print(f"📝 Error details saved to: {self.error_log}")
                
                # Show brief error summary
                if "auth" in result.stderr.lower() or "forbidden" in result.stderr.lower():
                    print("💡 Tip: Try logging in again or check if the Space is private.")
                elif "not found" in result.stderr.lower():
                    print("💡 Tip: The Space might be expired or the URL is incorrect.")
                
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Download timed out after 1 hour")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during download: {e}")
            return False
    
    def get_user_input(self):
        """Get user input with a nice interface"""
        print("\n" + "=" * 60)
        print("📝 LOGIN INFORMATION")
        print("=" * 60)
        
        username = input("👤 Twitter/X username: ").strip()
        if not username:
            print("❌ Username cannot be empty.")
            return None, None, None
            
        password = getpass.getpass("🔒 Twitter/X password: ")
        if not password:
            print("❌ Password cannot be empty.")
            return None, None, None
            
        mfa_code = input("🔐 MFA code (press Enter if not applicable): ").strip()
        if mfa_code == "":
            mfa_code = None
            
        return username, password, mfa_code
    
    def get_space_url(self):
        """Get and validate Space URL"""
        print("\n" + "=" * 60)
        print("🎙️  TWITTER SPACE URL")
        print("=" * 60)
        print("Example: https://x.com/i/spaces/1YpKklAePYBGj")
        
        while True:
            url = input("\n🔗 Enter Twitter Space URL: ").strip()
            if self.validate_space_url(url):
                return url
            else:
                print("❌ Invalid URL format. Please try again.")
                print("💡 URL should be: https://x.com/i/spaces/[SPACE_ID]")
    
    def run(self):
        """Main application loop"""
        try:
            self.print_header()
            
            # Check dependencies
            if not self.check_dependencies():
                input("\nPress Enter to exit...")
                return
            
            # Check authentication
            if not self.validate_cookies():
                username, password, mfa_code = self.get_user_input()
                if not username:
                    return
                
                if not asyncio.run(self.login_to_x(username, password, mfa_code)):
                    print("❌ Login failed after all attempts.")
                    input("\nPress Enter to exit...")
                    return
            
            # Get Space URL and download
            space_url = self.get_space_url()
            
            success = self.download_twitter_space(space_url)
            
            if success:
                print("\n🎉 Download completed successfully!")
                print(f"📂 Check your Downloads folder: {self.downloads_dir}")
            else:
                print("\n❌ Download failed. Check the error log for details.")
            
            print("\n" + "=" * 60)
            input("Press Enter to exit...")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            input("\nPress Enter to exit...")

def main():
    downloader = TwitterSpacesDownloader()
    downloader.run()

if __name__ == "__main__":
    main()
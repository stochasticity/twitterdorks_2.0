import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile

def download_file(url, filename):
    """Download a file from URL"""
    print(f"Downloading {filename}...")
    urllib.request.urlretrieve(url, filename)
    print(f"✅ Downloaded {filename}")

def main():
    print("=" * 70)
    print("🔨 BUILDING STANDALONE TWITTER SPACES DOWNLOADER")
    print("=" * 70)
    
    # Create build directory
    build_dir = "standalone_build"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)
    
    # Step 1: Download yt-dlp executable
    print("\n📦 Downloading yt-dlp executable...")
    ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    ytdlp_path = os.path.join(build_dir, "yt-dlp.exe")
    download_file(ytdlp_url, ytdlp_path)
    
    # Step 2: Download FFmpeg
    print("\n📦 Downloading FFmpeg...")
    # Using FFmpeg essentials build
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    ffmpeg_zip = os.path.join(build_dir, "ffmpeg.zip")
    download_file(ffmpeg_url, ffmpeg_zip)
    
    # Extract FFmpeg
    print("📂 Extracting FFmpeg...")
    with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
        zip_ref.extractall(build_dir)
    
    # Find ffmpeg.exe in extracted folders
    ffmpeg_exe = None
    for root, dirs, files in os.walk(build_dir):
        if "ffmpeg.exe" in files:
            ffmpeg_exe = os.path.join(root, "ffmpeg.exe")
            break
    
    if ffmpeg_exe:
        # Move ffmpeg.exe to build_dir root
        shutil.move(ffmpeg_exe, os.path.join(build_dir, "ffmpeg.exe"))
        print("✅ FFmpeg ready")
    
    # Clean up FFmpeg zip and folders
    os.remove(ffmpeg_zip)
    for item in os.listdir(build_dir):
        item_path = os.path.join(build_dir, item)
        if os.path.isdir(item_path) and "ffmpeg" in item.lower():
            shutil.rmtree(item_path)
    
    # Step 3: Copy the main script
    shutil.copy("clean_final_downloader.py", build_dir)
    
    # Step 4: Create the spec file
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['clean_final_downloader.py'],
    pathex=[],
    binaries=[
        ('yt-dlp.exe', '.'),
        ('ffmpeg.exe', '.')
    ],
    datas=[],
    hiddenimports=[
        'urllib3',
        'certifi',
        'ssl',
        '_ssl',
        'queue'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TwitterSpacesDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Don't use UPX compression
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)
'''
    
    spec_path = os.path.join(build_dir, "TwitterSpacesDownloader.spec")
    with open(spec_path, 'w') as f:
        f.write(spec_content)
    
    # Step 5: Build with PyInstaller
    print("\n🔨 Building executable with PyInstaller...")
    os.chdir(build_dir)
    
    try:
        subprocess.run([
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            "TwitterSpacesDownloader.spec"
        ], check=True)
        
        print("\n✅ Build successful!")
        print(f"📂 Executable location: {os.path.abspath('dist/TwitterSpacesDownloader.exe')}")
        
        # Copy the exe to parent directory
        final_exe = "../TwitterSpacesDownloader_Standalone.exe"
        shutil.copy("dist/TwitterSpacesDownloader.exe", final_exe)
        print(f"📂 Copied to: {os.path.abspath(final_exe)}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
    
    os.chdir("..")

if __name__ == "__main__":
    main()
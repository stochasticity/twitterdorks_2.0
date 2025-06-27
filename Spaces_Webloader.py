import asyncio
import datetime
import subprocess
import streamlit as st
from playwright.async_api import async_playwright
import os
import nest_asyncio
import threading
import shutil
import zipfile

#
#    TODO's: Still have to post example URL's for both Twitter and Youtube (and any other services this will work on)
#    Need to fix Login flow / Arkose Labs CAPTCHA challenge
#    
#

nest_asyncio.apply()
st.set_page_config(page_title="TwitterX Spaces Downloader", page_icon="🎹")

DATA_DIR = os.getcwd()
COOKIES_PATH = os.path.join(DATA_DIR, "cookies.txt")
download_result = {}

# --- Cleanup previous archives ---
for file in os.listdir(DATA_DIR):
    if file.startswith("twitter_space_") and file.endswith(".zip"):
        try:
            os.remove(os.path.join(DATA_DIR, file))
        except Exception:
            pass

if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright")):
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
        st.success("✅ Chromium installed successfully.")
    except Exception as e:
        st.error(f"❌ Playwright install failed: {e}")

async def login_to_x(username, password, mfa_code=None, challenge_value=None):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto("https://x.com/i/flow/login")
            await page.wait_for_selector("input[name='text']", timeout=20000)
            await page.fill("input[name='text']", username)
            await page.click("button:has-text('Next')")
            st.success("✅ Username entered and Next clicked.")

            try:
                await page.wait_for_selector("input[name='password']", timeout=8000)
            except:
                st.info("🔁 Detected email/phone challenge. Supplying challenge value...")
                await page.screenshot(path="screenshot_challenge_screen.png")
                await page.wait_for_selector("input[data-testid='ocfEnterTextTextInput']", timeout=10000)
                await page.fill("input[data-testid='ocfEnterTextTextInput']", challenge_value)

                html = await page.content()
                with open("challenge_debug.html", "w", encoding="utf-8") as f:
                    f.write(html)

                try:
                    st.info("🔍 Trying selector: button[data-testid='ocfEnterTextNextButton']")
                    btn = await page.wait_for_selector("button[data-testid='ocfEnterTextNextButton']", timeout=10000)
                    await btn.scroll_into_view_if_needed()
                    await btn.click(force=True)
                    st.success("✅ Clicked challenge Next button.")
                except Exception as e:
                    st.error(f"❌ Challenge screen click failed: {e}")
                    await page.screenshot(path="challenge_next_fail.png")
                    return False

                try:
                    await page.wait_for_selector("input[name='password']", timeout=20000)
                except:
                    error_box = await page.query_selector("//div[contains(text(), 'Incorrect. Please try again.')]")
                    if error_box:
                        st.error("❌ Challenge value rejected by Twitter.")
                        await page.screenshot(path="challenge_incorrect_value.png")
                        return False
                    else:
                        st.error("❌ Login failed: Password field not found after challenge.")
                        await page.screenshot(path="challenge_no_password.png")
                        return False

            await page.fill("input[name='password']", password)
            await page.click("button:has-text('Log in')")
            st.success("✅ Password entered and Log in clicked.")

            if mfa_code:
                try:
                    mfa_input = await page.wait_for_selector("input[data-testid='ocfEnterTextTextInput']", timeout=60000)
                    await mfa_input.fill(mfa_code)
                    await page.click("button[data-testid='ocfEnterTextNextButton']")
                    st.success("✅ MFA code entered and Next clicked.")
                except Exception as e:
                    st.warning(f"⚠️ MFA skipped or failed: {e}")

            await page.wait_for_timeout(5000)
            cookies = await context.cookies()
            with open(COOKIES_PATH, "w") as f:
                f.write("# Netscape HTTP Cookie File\n")
                for cookie in cookies:
                    f.write(
                        f"{cookie['domain']}\t"
                        f"{'TRUE' if cookie['domain'].startswith('.') else 'FALSE'}\t"
                        f"{cookie['path']}\t"
                        f"{'TRUE' if cookie.get('secure', False) else 'FALSE'}\t"
                        f"{int(cookie['expires']) if cookie.get('expires') else 0}\t"
                        f"{cookie['name']}\t"
                        f"{cookie['value']}\n"
                    )
            await browser.close()
            return True
    except Exception as e:
        st.error(f"❌ Login failed: {e}")
        return False

async def async_download_twitter_space(url):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"twitter_space_{timestamp}"
    audio_path = os.path.join(DATA_DIR, f"{base_filename}.m4a")
    info_path = os.path.join(DATA_DIR, f"{base_filename}.info.json")
    zip_path = os.path.join(DATA_DIR, f"{base_filename}.zip")

    command = [
        "yt-dlp", "--verbose",
        "--cookies", COOKIES_PATH,
        "--no-clean-info-json",
        "--write-info-json",
        "--write-comments",
        url,
        "-o", audio_path
    ]
    st.code(" ".join(command), language="bash")

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        st.success("✅ Download successful.")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(audio_path):
                zipf.write(audio_path, os.path.basename(audio_path))
                os.remove(audio_path)
            if os.path.exists(info_path):
                zipf.write(info_path, os.path.basename(info_path))
                os.remove(info_path)

        if os.path.exists(zip_path):
            download_result["path"] = zip_path
            download_result["name"] = os.path.basename(zip_path)
        else:
            st.error("⚠️ Archive missing after download.")
    else:
        st.error("❌ Download failed.")
        st.text(stderr.decode())
        with open(os.path.join(DATA_DIR, "yt_dlp_error.log"), "w") as log_file:
            log_file.write("YT-DLP Debug Information\n\n")
            log_file.write("Command:\n" + ' '.join(command) + "\n\n")
            log_file.write("STDERR:\n" + stderr.decode())

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

background_loop = asyncio.new_event_loop()
threading.Thread(target=start_background_loop, args=(background_loop,), daemon=True).start()

st.title("🎹 TwitterX Spaces Downloader")
st.caption("Download Twitter Spaces with yt-dlp + Playwright + Streamlit")

uploaded_cookie = st.file_uploader("📂 Upload cookies.txt (to skip login)", type=["txt"])
if uploaded_cookie:
    with open(COOKIES_PATH, "wb") as out_file:
        out_file.write(uploaded_cookie.read())
    st.success("✅ Cookies uploaded. Login step will be skipped.")

download_placeholder = st.empty()

with st.form("login_form"):
    username = st.text_input("TwitterX Username", max_chars=100)
    password = st.text_input("TwitterX Password", type="password")
    mfa_code = st.text_input("MFA Code (if applicable)", max_chars=10)
    challenge_value = st.text_input("Challenge: Email or Phone (if prompted)", max_chars=100)
    space_url = st.text_input("Twitter Space URL", placeholder="https://x.com/i/spaces/1mnxegnjbMPGX")
    submit = st.form_submit_button("Login & Download")

if submit:
    if not space_url:
        st.warning("Please enter the Space URL.")
    elif uploaded_cookie:
        st.success("🔐 Using uploaded cookies. Starting download...")
        with st.spinner("Downloading..."):
            asyncio.run(async_download_twitter_space(space_url))
    elif not username or not password:
        st.warning("Please enter username and password or upload cookies.")
    else:
        with st.spinner("Logging in..."):
            login_success = asyncio.run(login_to_x(username, password, mfa_code, challenge_value))
        if login_success:
            st.info("Login successful. Starting download in background...")
            with st.spinner("Downloading..."):
                asyncio.run(async_download_twitter_space(space_url))

if "path" in download_result and os.path.exists(download_result["path"]):
    with open(download_result["path"], "rb") as zf:
        download_placeholder.download_button(
            label="📆 Download Archived Twitter Space",
            data=zf,
            file_name=download_result["name"],
            mime="application/zip"
        )

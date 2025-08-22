#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
import base64
import requests
from typing import Optional

API_URL = "https://www.sms-console.jp/api/"
API_ID = "sm000206_user"                      # ← 后台里的 ID
API_PASSWORD = "reclab0601"  # ← 该用户的 API用パスワード

TARGET_NUMBER = "09044904649"
MESSAGE = "テスト送信です。"

# 是否启用送达结果通知（用到 status=1 + 合规 smsid）
USE_DELIVERY_REPORT = False

TIMEOUT = 15

PAT_11 = re.compile(r"^0(?:20[1-9]|60[1-9]|70[1-9]|80[1-9]|90[1-9])\d{7}$")
PAT_14 = re.compile(r"^0(?:200|600|700|800|900)\d{10}$")
PAT_81 = re.compile(r"^81(?:80|90)\d{8}$")

def only_digits(s: str) -> str:
    return re.sub(r"\D", "", str(s))

def classify_number(num: str):
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
    # 纯英数字、<=50
    return f"REQ{int(time.time())}"

def post_once(mobilenumber: str, smstext: str, use_report: bool) -> requests.Response:
    text = (smstext or "").replace("&", "＆")
    headers = {
        "Authorization": build_basic_auth(API_ID, API_PASSWORD),
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "python-requests/2.x",
        "Connection": "close",
    }
    data = {
        "mobilenumber": mobilenumber,
        "smstext": text,
    }
    if use_report:
        data["status"] = "1"           # 需要送达通知
        data["smsid"] = gen_alnum_smsid()  # 合规 smsid（英数字のみ）

    r = requests.post(API_URL, headers=headers, data=data, timeout=TIMEOUT, verify=True)
    print("STATUS:", r.status_code, "| SENT mobilenumber:", mobilenumber)
    print("BODY  :", r.text)
    return r

def send_sms(phone: str, text: str, use_report: bool = False):
    raw = only_digits(phone)
    kind = classify_number(raw)
    if not kind and raw.startswith("0") and len(raw) == 11:
        kind = "11"
    if not kind:
        raise SystemExit(f"手机号不符合规格：{phone}（清洗后：{raw}）")

    r = post_once(raw, text, use_report)
    if r.status_code != 560 or kind != "11":
        return

    alt = to_81_from_11(raw)
    print("⚠️ 收到 560，按规格表改用 81 形式再试：", alt)
    post_once(alt, text, use_report)

if __name__ == "__main__":
    print("→ 准备发送到", TARGET_NUMBER)
    try:
        send_sms(TARGET_NUMBER, MESSAGE, use_report=USE_DELIVERY_REPORT)
    except requests.RequestException as e:
        print("请求异常：", e)
    except Exception as e:
        print("运行时错误：", e)
    input("\n按回车键退出...")

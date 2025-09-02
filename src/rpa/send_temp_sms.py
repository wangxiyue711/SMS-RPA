#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时个人SMS发送脚本 - 绕过Firebase Admin SDK
使用网页传递的配置信息直接发送SMS
"""

import sys
import json
import os
import re
import base64
import time
import requests

# 安全的print函数，避免编码错误
def safe_print(message):
    try:
        print(message)
        sys.stdout.flush()
    except (UnicodeEncodeError, UnicodeError):
        try:
            ascii_message = str(message).encode('ascii', 'ignore').decode('ascii')
            print(ascii_message)
            sys.stdout.flush()
        except:
            print("MESSAGE_ENCODING_ERROR")
            sys.stdout.flush()

# ====== 从send_sms_once.py复制的SMS发送逻辑 ======

TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
USE_DELIVERY_REPORT = os.getenv("SMS_USE_REPORT", "0") == "1"

def only_digits(s: str) -> str:
    return re.sub(r"\D", "", str(s))

def build_basic_auth(user: str, pwd: str) -> str:
    token = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("utf-8")
    return f"Basic {token}"

def gen_alnum_smsid() -> str:
    return f"REQ{int(time.time())}"

def post_once(api_url: str, api_id: str, api_password: str, mobilenumber: str, smstext: str, use_report: bool) -> requests.Response:
    text = (smstext or "").replace("&", "＆")
    headers = {
        "Authorization": build_basic_auth(api_id, api_password),
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "python-requests/2.x",
        "Connection": "close",
    }
    data = {"mobilenumber": mobilenumber, "smstext": text}
    if use_report:
        data["status"] = "1"
        data["smsid"] = gen_alnum_smsid()
    
    safe_print(f"📡 Sending SMS API request to: {api_url}")
    safe_print(f"📱 Target phone: {mobilenumber}")
    safe_print(f"📝 Message length: {len(text)} chars")
    
    r = requests.post(api_url, headers=headers, data=data, timeout=TIMEOUT)
    
    # 状态码映射
    code_map = {
        200: '成功',
        401: '认证错误（Authorization Required）',
        402: '发送上限错误（Overlimit）',
        560: '手机号无效',
        # ... 更多状态码
    }
    
    msg = code_map.get(r.status_code, '未知错误')
    safe_print(f"STATUS: {r.status_code} ({msg}) | SENT mobilenumber: {mobilenumber}")
    safe_print(f"RESPONSE: {r.text[:500]}")
    
    return r

def send_sms(api_url: str, api_id: str, api_password: str, phone: str, text: str, use_report: bool = False):
    """发送SMS"""
    # 处理手机号格式
    raw = only_digits(phone)
    if raw.startswith("81") and len(raw) == 11:
        local_num = "0" + raw[2:]
    elif raw.startswith("0") and len(raw) == 11:
        local_num = raw
    else:
        # 如果是10位数字，前面加0
        if len(raw) == 10:
            local_num = "0" + raw
        else:
            raise ValueError(f"手机号格式不正确：{phone}")
    
    safe_print(f"发送本地格式手机号：{local_num}")
    r = post_once(api_url, api_id, api_password, local_num, text, use_report)
    
    if r.status_code == 560:
        # 尝试81格式
        alt = "81" + local_num[1:]
        safe_print(f"⚠️ 收到 560，改用 81 形式再试：{alt}")
        r = post_once(api_url, api_id, api_password, alt, text, use_report)
    
    return r

def main():
    try:
        # 从标准输入读取JSON数据
        input_line = sys.stdin.readline().strip()
        if not input_line:
            safe_print("ERROR: No input data received")
            sys.exit(1)
            
        data = json.loads(input_line)
        
        user_uid = data.get('userUid')
        phone = data.get('phone')
        message = data.get('message')
        
        # 新增：直接从输入获取SMS配置
        sms_config = data.get('smsConfig', {})
        
        if not all([user_uid, phone, message]):
            safe_print("ERROR: Missing required parameters (userUid, phone, message)")
            sys.exit(1)
        
        # 检查SMS配置
        api_url = sms_config.get('api_url', '')
        api_id = sms_config.get('api_id', '')
        api_password = sms_config.get('api_password', '')
        
        if not all([api_url, api_id, api_password]):
            safe_print("ERROR: SMS configuration missing. Please set SMS API settings in web interface.")
            safe_print(f"api_url: {bool(api_url)}, api_id: {bool(api_id)}, api_password: {bool(api_password)}")
            sys.exit(1)
        
        safe_print(f"Starting SMS send to: {phone}")
        safe_print(f"Using API: {api_url}")
        
        # 发送SMS
        response = send_sms(api_url, api_id, api_password, phone, message, USE_DELIVERY_REPORT)
        
        if response.status_code == 200:
            safe_print(f"SUCCESS: SMS sent successfully")
            sys.exit(0)
        else:
            safe_print(f"ERROR: SMS sending failed - HTTP {response.status_code}")
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        safe_print(f"ERROR: Invalid JSON input: {e}")
        sys.exit(1)
    except Exception as e:
        safe_print(f"ERROR: Script execution failed: {e}")
        import traceback
        safe_print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()

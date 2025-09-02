#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单SMS发送工具 - 无需Node.js服务器
直接在命令行运行即可发送SMS
"""

import re
import base64
import time
import requests

def send_sms_simple():
    print("=== 简单SMS发送工具 ===")
    print()
    
    # 1. 获取SMS API配置
    print("请输入您的SMS API配置:")
    api_url = input("API URL (默认: https://www.sms-console.jp/api/): ").strip()
    if not api_url:
        api_url = "https://www.sms-console.jp/api/"
    
    api_id = input("API ID: ").strip()
    api_password = input("API Password: ").strip()
    
    if not api_id or not api_password:
        print("❌ API ID和密码不能为空！")
        return
    
    print()
    
    # 2. 获取手机号和消息
    phone = input("手机号 (例如: 09012345678): ").strip()
    message = input("短信内容: ").strip()
    
    if not phone or not message:
        print("❌ 手机号和短信内容不能为空！")
        return
    
    print()
    print("=== 开始发送SMS ===")
    
    try:
        # 3. 处理手机号格式
        raw = re.sub(r"\D", "", phone)  # 去除非数字字符
        
        if raw.startswith("81") and len(raw) == 11:
            local_num = "0" + raw[2:]  # +81xx -> 0xx
        elif raw.startswith("0") and len(raw) == 11:
            local_num = raw  # 已经是0开头
        elif len(raw) == 10:
            local_num = "0" + raw  # 10位数字前加0
        else:
            print(f"❌ 手机号格式不正确: {phone}")
            return
        
        print(f"📱 发送到: {local_num}")
        print(f"📝 消息: {message}")
        print(f"🌐 API: {api_url}")
        
        # 4. 发送SMS
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_id}:{api_password}'.encode()).decode()}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "python-requests/2.x"
        }
        
        data = {
            "mobilenumber": local_num,
            "smstext": message.replace("&", "＆")
        }
        
        print("📡 正在发送...")
        response = requests.post(api_url, headers=headers, data=data, timeout=15)
        
        # 5. 显示结果
        print()
        print("=== 发送结果 ===")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("✅ SMS发送成功！")
        else:
            print("❌ SMS发送失败")
            
            # 状态码说明
            error_codes = {
                401: "认证错误 - 请检查API ID和密码",
                402: "发送上限错误",
                560: "手机号无效 - 请检查手机号格式",
                666: "即将IP封禁（认证错误过多）"
            }
            
            if response.status_code in error_codes:
                print(f"💡 {error_codes[response.status_code]}")
        
    except Exception as e:
        print(f"❌ 发送过程出错: {e}")

if __name__ == "__main__":
    try:
        send_sms_simple()
    except KeyboardInterrupt:
        print("\n\n👋 已取消发送")
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
    
    input("\n按回车键退出...")

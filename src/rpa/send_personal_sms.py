#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
个人SMS发送脚本 - 使用Firebase配置，参考send_sms_once.py的SMS发送逻辑
接收JSON格式的输入，发送单条SMS
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
        # 如果遇到编码错误，使用ASCII编码
        try:
            ascii_message = str(message).encode('ascii', 'ignore').decode('ascii')
            print(ascii_message)
            sys.stdout.flush()
        except:
            print("MESSAGE_ENCODING_ERROR")
            sys.stdout.flush()

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    safe_print("✅ Firebase Admin SDK imported successfully")
except ImportError:
    safe_print("❌ Firebase Admin SDK not installed. Run: pip install firebase-admin")
    sys.exit(1)

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
                # 尝试多个可能的密钥路径
                key_paths = [
                    os.path.join(os.path.dirname(__file__), "../../config/firebase/firebase-service-account.json"),
                    "firebase-service-account.json",
                    os.path.join("config", "firebase", "firebase-service-account.json")
                ]
                
                cred = None
                for key_path in key_paths:
                    if os.path.exists(key_path):
                        cred = credentials.Certificate(key_path)
                        safe_print(f"✅ Found Firebase key at: {key_path}")
                        break
                
                if cred:
                    firebase_admin.initialize_app(cred)
                    safe_print("✅ Firebase Admin initialized with service account")
                else:
                    # 如果没有服务账户密钥，使用环境变量或跳过Firebase Admin初始化
                    safe_print("⚠️ No Firebase service account key found")
                    safe_print("⚠️ Trying alternative configuration method...")
                    
                    # 尝试直接返回配置而不使用Firebase Admin
                    return self.get_config_from_environment(user_uid)
            
            self.db = firestore.client()
            self.user_uid = user_uid
            
            # 获取用户配置
            doc_ref = self.db.collection('user_configs').document(user_uid)
            doc = doc_ref.get()
            
            if doc.exists:
                self.user_config = doc.to_dict()
                safe_print(f"✅ 用户配置获取成功: {user_uid}")
                return True
            else:
                safe_print(f"❌ 用户配置不存在: {user_uid}")
                return False
                
        except Exception as e:
            safe_print(f"❌ Firebase初始化失败: {e}")
            return False
    
    def get_config_from_environment(self, user_uid: str):
        """从环境变量获取配置（当Firebase服务账户密钥不可用时）"""
        try:
            safe_print("🔧 Using fallback configuration method")
            
            # 模拟用户配置结构
            self.user_config = {
                'sms': {
                    'api_url': os.getenv('SMS_API_URL', 'https://www.sms-console.jp/api/'),
                    'api_id': os.getenv('SMS_API_ID', ''),
                    'api_password': os.getenv('SMS_API_PASSWORD', '')
                }
            }
            
            # 检查配置是否完整
            sms_config = self.user_config.get('sms', {})
            if not sms_config.get('api_id') or not sms_config.get('api_password'):
                safe_print("❌ SMS配置不完整，请设置环境变量:")
                safe_print("   SMS_API_ID=您的API_ID")
                safe_print("   SMS_API_PASSWORD=您的API密码")
                return False
            
            safe_print(f"✅ 环境变量配置获取成功: {user_uid}")
            return True
            
        except Exception as e:
            safe_print(f"❌ 环境变量配置获取失败: {e}")
            return False
    
    def get_sms_config(self):
        """获取SMS配置"""
        if not self.user_config:
            return {}
        return self.user_config.get('sms', {})

# 全局Firebase配置实例
firebase_config = FirebaseConfig()

# ====== 从send_sms_once.py复制的SMS发送逻辑 ======

# 默认配置（可以被环境变量覆盖）
TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))
USE_DELIVERY_REPORT = os.getenv("SMS_USE_REPORT", "0") == "1"

# 电话号码规范化与校验
PAT_11 = re.compile(r"^0(?:20[1-9]|60[1-9]|70[1-9]|80[1-9]|90[1-9])\d{7}$")
PAT_14 = re.compile(r"^0(?:200|600|700|800|900)\d{10}$")
PAT_81 = re.compile(r"^81(?:70|80|90)\d{8}$")  # 支持+81 xx xxxx xxxx等带空格格式

def only_digits(s: str) -> str:
    # 去除所有非数字字符
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
    
    # 状态码详细说明映射（从send_sms_once.py复制）
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
    safe_print(f"STATUS: {r.status_code} ({msg}) | SENT mobilenumber: {mobilenumber}")
    safe_print(f"RESPONSE: {r.text[:500]}")
    
    # 响应内容判断
    if r.status_code != 200 or ("error" in r.text.lower() or "fail" in r.text.lower()):
        safe_print("⚠️ API响应异常，内容如下：")
        safe_print(r.text)
    
    return r

def send_sms(api_url: str, api_id: str, api_password: str, phone: str, text: str, use_report: bool = False):
    """发送SMS - 参考send_sms_once.py的逻辑"""
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
        raise ValueError(f"手机号不符合日本本地格式：{phone}（清洗后：{raw}）")
    
    safe_print(f"发送本地格式手机号：{local_num}")
    r = post_once(api_url, api_id, api_password, local_num, text, use_report)
    
    if r.status_code == 560:
        # 兜底再试81格式
        alt = "81" + local_num[1:]
        safe_print(f"⚠️ 收到 560，改用 81 形式再试：{alt}")
        r = post_once(api_url, api_id, api_password, alt, text, use_report)
    
    return r

class PersonalSMSSender:
    def __init__(self):
        pass
        
    def get_user_config_from_firebase(self, user_uid):
        """从Firebase获取用户配置"""
        try:
            # 初始化Firebase配置
            if not firebase_config.initialize_firebase(user_uid):
                safe_print("❌ Firebase初始化失败")
                return None
            
            # 获取SMS配置
            sms_config = firebase_config.get_sms_config()
            
            if not sms_config:
                safe_print("❌ 用户SMS配置为空")
                return None
            
            # 验证必要的配置项
            required_fields = ['api_url', 'api_id', 'api_password']
            missing_fields = [field for field in required_fields if not sms_config.get(field)]
            
            if missing_fields:
                safe_print(f"❌ SMS配置不完整，缺少: {missing_fields}")
                return None
            
            config = {
                'sms': sms_config
            }
            
            safe_print("✅ 从Firebase获取SMS配置成功")
            return config
            
        except Exception as e:
            safe_print(f"❌ 获取Firebase配置失败: {e}")
            return None
    
    def send_personal_sms(self, config, phone, message):
        """发送个人SMS"""
        try:
            sms_config = config.get('sms', {})
            api_url = sms_config.get('api_url', '')
            api_id = sms_config.get('api_id', '')
            api_password = sms_config.get('api_password', '')
            
            if not all([api_url, api_id, api_password]):
                return False, "SMS配置不完整"
            
            # 使用send_sms_once.py的发送逻辑
            response = send_sms(api_url, api_id, api_password, phone, message, USE_DELIVERY_REPORT)
            
            if response.status_code == 200:
                return True, f"SMS发送成功: {response.text}"
            else:
                return False, f"SMS发送失败: HTTP {response.status_code} - {response.text}"
                
        except Exception as e:
            return False, f"SMS发送异常: {str(e)}"

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
        
        if not all([user_uid, phone, message]):
            safe_print("ERROR: Missing required parameters (userUid, phone, message)")
            sys.exit(1)
        
        safe_print(f"Starting SMS send to: {phone}")
        
        # 初始化个人SMS发送器
        sender = PersonalSMSSender()
        
        # 获取用户配置
        config = sender.get_user_config_from_firebase(user_uid)
        if not config:
            safe_print("ERROR: Failed to get SMS config")
            sys.exit(1)
        
        # 发送SMS
        success, result_message = sender.send_personal_sms(config, phone, message)
        
        if success:
            safe_print(f"SUCCESS: {result_message}")
            sys.exit(0)
        else:
            safe_print(f"ERROR: {result_message}")
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

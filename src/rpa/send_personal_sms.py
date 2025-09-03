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

# Windows编码设置
import locale
try:
    # 尝试设置UTF-8编码
    if sys.platform.startswith('win'):
        # 设置环境变量 - 这是最安全的方法
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        # 不使用chcp命令，因为在Node.js子进程中可能失败
except Exception as e:
    # 如果设置失败，继续执行，但可能会有编码问题
    pass

# 安全的print函数，支持日语字符 - 针对Windows优化
def safe_print(message):
    try:
        # 尝试直接输出
        print(str(message))
        # 在Node.js子进程中，flush可能会有问题，所以加try-catch
        try:
            sys.stdout.flush()
        except:
            pass
    except UnicodeEncodeError:
        try:
            # 如果有编码问题，尝试用UTF-8编码
            encoded_msg = str(message).encode('utf-8', errors='replace').decode('utf-8')
            print(encoded_msg)
            try:
                sys.stdout.flush()
            except:
                pass
        except:
            # 最后的备选方案：输出无日语的简化版本
            try:
                # 尝试只保留ASCII字符和数字
                ascii_msg = ''.join(char if ord(char) < 128 else '?' for char in str(message))
                print(f"[INFO] {ascii_msg}")
                try:
                    sys.stdout.flush()
                except:
                    pass
            except:
                print("[MESSAGE_ENCODING_HANDLED]")
                try:
                    sys.stdout.flush()
                except:
                    pass
    except Exception as e:
        try:
            print(f"[PRINT_ERROR] {type(e).__name__}")
            try:
                sys.stdout.flush()
            except:
                pass
        except:
            pass

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    safe_print("Firebase Admin SDK imported successfully")
except ImportError:
    safe_print("Firebase Admin SDK not installed. Run: pip install firebase-admin")
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
                # 尝试多个可能的密钥路径 - 现在工作目录是项目根目录
                key_paths = [
                    # 从项目根目录出发的路径（Node.js现在设置的工作目录）
                    os.path.join("config", "firebase", "firebase-service-account.json"),
                    # 从脚本文件位置出发的路径（终端直接运行时）
                    os.path.join(os.path.dirname(__file__), "../../config/firebase/firebase-service-account.json"),
                    # 绝对路径备用
                    os.path.abspath("config/firebase/firebase-service-account.json"),
                    # 直接文件名（如果在同目录）
                    "firebase-service-account.json"
                ]
                
                safe_print("Firebase key file check:")
                cred = None
                for key_path in key_paths:
                    abs_path = os.path.abspath(key_path)
                    exists = os.path.exists(key_path)
                    safe_print(f"Trying path: {abs_path} - Exists: {exists}")
                    if exists:
                        try:
                            cred = credentials.Certificate(key_path)
                            safe_print(f"Firebase key loaded successfully: {key_path}")
                            break
                        except Exception as e:
                            safe_print(f"Firebase key load failed: {e}")
                            continue
                
                if cred:
                    firebase_admin.initialize_app(cred)
                    safe_print("Firebase Admin initialized with service account")
                else:
                    # 如果没有服务账户密钥，使用环境变量或跳过Firebase Admin初始化
                    safe_print("No Firebase service account key found")
                    safe_print("Trying alternative configuration method...")
                    
                    # 尝试直接返回配置而不使用Firebase Admin
                    return self.get_config_from_environment(user_uid)
            
            self.db = firestore.client()
            self.user_uid = user_uid
            
            # 获取用户配置
            doc_ref = self.db.collection('user_configs').document(user_uid)
            doc = doc_ref.get()
            
            if doc.exists:
                self.user_config = doc.to_dict()
                safe_print(f"User config retrieved successfully: {user_uid}")
                return True
            else:
                safe_print(f"User config not found: {user_uid}")
                return False
                
        except Exception as e:
            safe_print(f"Firebase initialization failed: {e}")
            return False
    
    def get_config_from_environment(self, user_uid: str):
        """从环境变量获取配置（当Firebase服务账户密钥不可用时）"""
        try:
            safe_print("Using fallback configuration method")
            
            # 模拟用户配置结构 - 使用sms_config字段匹配HTML结构
            self.user_config = {
                'sms_config': {
                    'api_url': os.getenv('SMS_API_URL', 'https://www.sms-console.jp/api/'),
                    'api_id': os.getenv('SMS_API_ID', ''),
                    'api_password': os.getenv('SMS_API_PASSWORD', '')
                }
            }
            
            # 检查配置是否完整
            sms_config = self.user_config.get('sms_config', {})
            if not sms_config.get('api_id') or not sms_config.get('api_password'):
                safe_print("SMS config incomplete, please set environment variables:")
                safe_print("   SMS_API_ID=your_api_id")
                safe_print("   SMS_API_PASSWORD=your_api_password")
                return False
            
            safe_print(f"Environment config retrieved successfully: {user_uid}")
            return True
            
        except Exception as e:
            safe_print(f"Environment config retrieval failed: {e}")
            return False
    
    def get_sms_config(self):
        """获取SMS配置 - 修正字段名匹配HTML保存的结构"""
        if not self.user_config:
            safe_print("User config is empty")
            return {}
        
        # 调试：显示用户配置的所有字段
        safe_print(f"User config fields: {list(self.user_config.keys())}")
        
        # HTML保存的是sms_config，不是sms
        sms_config = self.user_config.get('sms_config', {})
        
        # 调试：打印SMS配置内容
        safe_print(f"SMS config content: {sms_config}")
        
        return sms_config

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
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "python-requests/2.x",
        "Connection": "close",
    }
    data = {"mobilenumber": mobilenumber, "smstext": text}
    if use_report:
        data["status"] = "1"
        data["smsid"] = gen_alnum_smsid()
    
    safe_print(f"Sending SMS API request to: {api_url}")
    safe_print(f"Target phone: {mobilenumber}")
    safe_print(f"Message: {text}")
    safe_print(f"Message length: {len(text)} chars")
    
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
    
    # 详细分析SMS API响应
    response_text = r.text.strip()
    safe_print(f"Detailed response analysis:")
    safe_print(f"   Status code: {r.status_code}")
    safe_print(f"   Response length: {len(response_text)} chars")
    safe_print(f"   Response content: '{response_text}'")
    
    # 检查常见的限制问题
    if r.status_code == 402:
        safe_print("Send limit error: SMS account quota exhausted or send limit reached")
        safe_print("   Suggestion: Check SMS account balance, purchase more quota")
    elif r.status_code == 405:
        safe_print("Method not allowed: Possibly too frequent sending or account restricted")
        safe_print("   Suggestion: Wait 1 hour and retry, control sending frequency")
    elif r.status_code == 503:
        safe_print("Service temporarily unavailable: Possible temporary throttling")
        safe_print("   Suggestion: Wait 10-30 minutes and retry")
    elif r.status_code == 555:
        safe_print("IP banned: Too frequent sending, IP temporarily banned")
        safe_print("   Suggestion: Wait 1-2 hours and retry, or contact service provider")
    elif r.status_code == 585:
        safe_print("Invalid SMS content: Content filtered or contains prohibited words")
        safe_print("   Suggestion: Change SMS content, avoid test words")
    elif r.status_code == 592:
        safe_print("Exceeded send permission: Invalid time or exceeded send permission")
        safe_print("   Suggestion: Check account permission settings")
    elif r.status_code == 606:
        safe_print("API disabled: SMS API functionality disabled")
        safe_print("   Suggestion: Contact SMS service provider to reactivate API")
    elif r.status_code == 624:
        safe_print("Duplicate SMS ID: Possibly duplicate sending of same content")
        safe_print("   Suggestion: Change SMS content or wait and retry")
    elif r.status_code == 666:
        safe_print("About to be IP banned: 9 authentication errors, about to be banned")
        safe_print("   Suggestion: Stop sending immediately, check API key")
    elif r.status_code in [575, 576, 577, 578]:
        safe_print(f"Carrier restriction: {code_map.get(r.status_code, 'carrier related error')}")
        safe_print("   Suggestion: Check carrier support for target phone number")
    
    # 检查是否为真正的成功响应
    if r.status_code == 200:
        if response_text == "200":
            safe_print("Notice: API returned simple '200'")
            safe_print("   This may indicate:")
            safe_print("   1. Request accepted but quota exhausted")
            safe_print("   2. Content filtered (like test content)")
            safe_print("   3. Number in blacklist")
            safe_print("   4. Send frequency limit reached")
        elif "success" in response_text.lower() or "ok" in response_text.lower():
            safe_print("API response indicates successful sending")
        else:
            safe_print("API response unclear, suggest checking service provider account status")
    
    
    # 响应内容判断
    if r.status_code != 200 or ("error" in r.text.lower() or "fail" in r.text.lower()):
        safe_print("API response abnormal, content as follows:")
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
        raise ValueError(f"Phone number format error: {phone} (cleaned: {raw})")
    
    safe_print(f"Sending to local format phone: {local_num}")
    r = post_once(api_url, api_id, api_password, local_num, text, use_report)
    
    if r.status_code == 560:
        # 兜底再试81格式
        alt = "81" + local_num[1:]
        safe_print(f"Received 560, trying 81 format: {alt}")
        r = post_once(api_url, api_id, api_password, alt, text, use_report)
    
    return r

class PersonalSMSSender:
    def __init__(self):
        pass
        
    def get_user_config_from_firebase(self, user_uid):
        """从Firebase获取用户配置"""
        try:
            safe_print(f"Starting to get user config: {user_uid}")
            
            # 初始化Firebase配置
            if not firebase_config.initialize_firebase(user_uid):
                safe_print("Firebase initialization failed")
                return None
            
            # 获取SMS配置
            sms_config = firebase_config.get_sms_config()
            
            if not sms_config:
                safe_print("User SMS config is empty")
                return None
            
            # 调试：显示获取到的配置
            safe_print(f"Retrieved SMS config fields: {list(sms_config.keys())}")
            
            # 验证必要的配置项
            required_fields = ['api_url', 'api_id', 'api_password']
            missing_fields = [field for field in required_fields if not sms_config.get(field)]
            
            if missing_fields:
                safe_print(f"SMS config incomplete, missing: {missing_fields}")
                safe_print(f"Current config: {sms_config}")
                return None
            
            # 直接返回sms_config，保持字段一致性
            safe_print("SMS config retrieved from Firebase successfully")
            safe_print(f"API URL: {sms_config.get('api_url', 'N/A')}")
            safe_print(f"API ID: {sms_config.get('api_id', 'N/A')}")
            return sms_config
            
        except Exception as e:
            safe_print(f"Failed to get Firebase config: {e}")
            import traceback
            safe_print(f"Detailed error: {traceback.format_exc()}")
            return None
    
    def send_personal_sms(self, config, phone, message):
        """发送个人SMS"""
        try:
            # 现在config直接就是sms_config
            api_url = config.get('api_url', '')
            api_id = config.get('api_id', '')
            api_password = config.get('api_password', '')
            
            safe_print(f"Using config to send SMS:")
            safe_print(f"   API URL: {api_url}")
            safe_print(f"   API ID: {api_id}")
            safe_print(f"   Phone: {phone}")
            safe_print(f"   Message: {message}")
            
            if not all([api_url, api_id, api_password]):
                return False, "SMS config incomplete"
            
            # 使用send_sms_once.py的发送逻辑
            response = send_sms(api_url, api_id, api_password, phone, message, USE_DELIVERY_REPORT)
            
            if response.status_code == 200:
                return True, f"SMS sent successfully: {response.text}"
            else:
                return False, f"SMS send failed: HTTP {response.status_code} - {response.text}"
                
        except Exception as e:
            safe_print(f"SMS send exception details: {str(e)}")
            import traceback
            safe_print(f"Exception stack: {traceback.format_exc()}")
            return False, f"SMS send exception: {str(e)}"

def main():
    try:
        safe_print("SCRIPT_START: Starting send_personal_sms.py")
        safe_print(f"SCRIPT_CWD: Current working directory: {os.getcwd()}")
        safe_print(f"SCRIPT_FILE: Script file location: {__file__}")
        safe_print(f"SCRIPT_ENV: PYTHONIOENCODING = {os.getenv('PYTHONIOENCODING', 'NOT_SET')}")
        
        # 从标准输入读取JSON数据
        input_line = sys.stdin.readline().strip()
        if not input_line:
            safe_print("ERROR: No input data received")
            sys.exit(1)
            
        safe_print(f"SCRIPT_INPUT: Received input data: {input_line}")
        
        data = json.loads(input_line)
        
        user_uid = data.get('userUid')
        phone = data.get('phone')
        message = data.get('message')
        
        safe_print(f"Received parameters:")
        safe_print(f"   User UID: {user_uid}")
        safe_print(f"   Phone: {phone}")
        safe_print(f"   Message: {message}")
        
        if not all([user_uid, phone, message]):
            safe_print("ERROR: Missing required parameters (userUid, phone, message)")
            safe_print(f"Parameter check: userUid={bool(user_uid)}, phone={bool(phone)}, message={bool(message)}")
            sys.exit(1)
        
        safe_print(f"Starting SMS send to: {phone}")
        safe_print(f"Message content: {message}")
        
        # 初始化个人SMS发送器
        safe_print("SCRIPT_INIT: Creating PersonalSMSSender")
        sender = PersonalSMSSender()
        
        # 获取用户配置
        safe_print("SCRIPT_CONFIG: Getting user config from Firebase")
        config = sender.get_user_config_from_firebase(user_uid)
        if not config:
            safe_print("ERROR: Failed to get SMS config")
            sys.exit(1)
        
        # 发送SMS
        safe_print("SCRIPT_SEND: Sending SMS")
        success, result_message = sender.send_personal_sms(config, phone, message)
        
        if success:
            safe_print(f"SUCCESS: {result_message}")
            safe_print("SCRIPT_EXIT_SUCCESS")  # 明确的成功标识
            sys.exit(0)
        else:
            safe_print(f"ERROR: {result_message}")
            safe_print("SCRIPT_EXIT_FAILURE")  # 明确的失败标识
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

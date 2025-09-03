const express = require("express");
const { spawn } = require("child_process");
const cors = require("cors");
const path = require("path");
const fs = require("fs");

const app = express();
const PORT = 8888;

// 中间件
app.use(cors());
app.use(express.json());

// 存储正在运行的RPA进程
let rpaProcesses = new Map();

// 启动RPA脚本
app.post("/api/rpa/start", async (req, res) => {
  try {
    const { userUid, mode = "1", interval = 5 } = req.body;

    if (!userUid) {
      return res.status(400).json({
        success: false,
        error: "User UID is required",
      });
    }

    // 检查是否已有进程运行
    if (rpaProcesses.has(userUid)) {
      return res.status(400).json({
        success: false,
        error: "RPA process already running for this user",
      });
    }

    // Python脚本路径
    const scriptPath = path.join(
      __dirname,
      "..",
      "rpa",
      "send_sms_firebase.py"
    );

    // 检查脚本是否存在
    if (!fs.existsSync(scriptPath)) {
      return res.status(500).json({
        success: false,
        error: "RPA script not found",
      });
    }

    console.log(`🚀 Starting RPA for user: ${userUid}, mode: ${mode}`);

    // 启动Python进程
    const pythonProcess = spawn("python", [scriptPath], {
      cwd: __dirname,
      stdio: ["pipe", "pipe", "pipe"],
    });

    // 处理Python脚本的输入（自动输入用户UID和模式）
    pythonProcess.stdin.write(`${userUid}\n`);
    pythonProcess.stdin.write(`${mode}\n`);
    if (mode === "2") {
      pythonProcess.stdin.write(`${interval}\n`);
    }

    // 存储进程引用
    rpaProcesses.set(userUid, {
      process: pythonProcess,
      startTime: new Date(),
      mode: mode,
      logs: [],
    });

    // 监听输出
    pythonProcess.stdout.on("data", (data) => {
      const output = data.toString();
      console.log(`[RPA-${userUid}] STDOUT:`, output);

      // 存储日志
      const processInfo = rpaProcesses.get(userUid);
      if (processInfo) {
        processInfo.logs.push({
          type: "stdout",
          message: output,
          timestamp: new Date(),
        });
        // 只保留最近100条日志
        if (processInfo.logs.length > 100) {
          processInfo.logs = processInfo.logs.slice(-100);
        }
      }
    });

    pythonProcess.stderr.on("data", (data) => {
      const output = data.toString();
      console.error(`[RPA-${userUid}] STDERR:`, output);

      // 存储错误日志
      const processInfo = rpaProcesses.get(userUid);
      if (processInfo) {
        processInfo.logs.push({
          type: "stderr",
          message: output,
          timestamp: new Date(),
        });
      }
    });

    pythonProcess.on("close", (code) => {
      console.log(`[RPA-${userUid}] Process exited with code: ${code}`);

      // 更新进程状态
      const processInfo = rpaProcesses.get(userUid);
      if (processInfo) {
        processInfo.exitCode = code;
        processInfo.endTime = new Date();
        processInfo.status = "completed";
      }

      // 延迟删除进程信息（保留30分钟用于日志查看）
      setTimeout(() => {
        rpaProcesses.delete(userUid);
      }, 30 * 60 * 1000);
    });

    pythonProcess.on("error", (error) => {
      console.error(`[RPA-${userUid}] Process error:`, error);

      // 更新进程状态
      const processInfo = rpaProcesses.get(userUid);
      if (processInfo) {
        processInfo.error = error.message;
        processInfo.status = "error";
      }
    });

    res.json({
      success: true,
      message: "RPA process started successfully",
      processId: userUid,
      mode: mode,
      startTime: new Date(),
    });
  } catch (error) {
    console.error("Error starting RPA:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// 停止RPA脚本
app.post("/api/rpa/stop", (req, res) => {
  try {
    const { userUid } = req.body;

    if (!userUid) {
      return res.status(400).json({
        success: false,
        error: "User UID is required",
      });
    }

    const processInfo = rpaProcesses.get(userUid);
    if (!processInfo) {
      return res.status(404).json({
        success: false,
        error: "No RPA process found for this user",
      });
    }

    // 终止进程
    processInfo.process.kill("SIGTERM");
    processInfo.status = "stopped";
    processInfo.endTime = new Date();

    console.log(`🛑 Stopped RPA for user: ${userUid}`);

    res.json({
      success: true,
      message: "RPA process stopped successfully",
    });
  } catch (error) {
    console.error("Error stopping RPA:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// 获取RPA状态
app.get("/api/rpa/status/:userUid", (req, res) => {
  try {
    const { userUid } = req.params;

    const processInfo = rpaProcesses.get(userUid);

    if (!processInfo) {
      return res.json({
        success: true,
        status: "not_running",
        message: "No RPA process found",
      });
    }

    const status = {
      success: true,
      status: processInfo.status || "running",
      processId: userUid,
      mode: processInfo.mode,
      startTime: processInfo.startTime,
      endTime: processInfo.endTime,
      exitCode: processInfo.exitCode,
      error: processInfo.error,
      logCount: processInfo.logs.length,
    };

    res.json(status);
  } catch (error) {
    console.error("Error getting RPA status:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// 获取RPA日志
app.get("/api/rpa/logs/:userUid", (req, res) => {
  try {
    const { userUid } = req.params;
    const { limit = 50 } = req.query;

    const processInfo = rpaProcesses.get(userUid);

    if (!processInfo) {
      return res.json({
        success: true,
        logs: [],
        message: "No RPA process found",
      });
    }

    // 返回最近的日志
    const logs = processInfo.logs.slice(-parseInt(limit));

    res.json({
      success: true,
      logs: logs,
      totalLogs: processInfo.logs.length,
    });
  } catch (error) {
    console.error("Error getting RPA logs:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// 获取所有活跃的RPA进程
app.get("/api/rpa/processes", (req, res) => {
  try {
    const processes = Array.from(rpaProcesses.entries()).map(
      ([userUid, info]) => ({
        userUid,
        status: info.status || "running",
        mode: info.mode,
        startTime: info.startTime,
        endTime: info.endTime,
        logCount: info.logs.length,
      })
    );

    res.json({
      success: true,
      processes: processes,
      totalCount: processes.length,
    });
  } catch (error) {
    console.error("Error getting RPA processes:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// SMS个别发送
app.post("/api/sms/send", async (req, res) => {
  try {
    const { userUid, phone, message } = req.body;

    if (!userUid || !phone || !message) {
      return res.status(400).json({
        success: false,
        error: "User UID, phone number, and message are required",
      });
    }

    console.log(`📱 Sending SMS for user: ${userUid}, to: ${phone}`);

    // 检查是否有SMS配置环境变量
    const hasEnvConfig =
      process.env.SMS_API_URL &&
      process.env.SMS_API_ID &&
      process.env.SMS_API_PASSWORD;

    let smsScriptPath;
    let inputData;

    if (hasEnvConfig) {
      // 使用环境变量配置的临时脚本
      smsScriptPath = path.join(__dirname, "..", "rpa", "send_temp_sms.py");
      inputData = JSON.stringify({
        userUid: userUid,
        phone: phone,
        message: message,
        smsConfig: {
          api_url: process.env.SMS_API_URL,
          api_id: process.env.SMS_API_ID,
          api_password: process.env.SMS_API_PASSWORD,
        },
      });
    } else {
      // 使用Firebase配置的原始脚本
      smsScriptPath = path.join(__dirname, "..", "rpa", "send_personal_sms.py");
      inputData = JSON.stringify({
        userUid: userUid,
        phone: phone,
        message: message,
      });
    }

    // 检查脚本是否存在
    if (!fs.existsSync(smsScriptPath)) {
      console.log("❌ SMS script not found:", smsScriptPath);
      return res.status(500).json({
        success: false,
        error: `SMS script not found: ${path.basename(smsScriptPath)}`,
      });
    }

    console.log(`Using SMS script: ${path.basename(smsScriptPath)}`);

    // 启动Python进程发送SMS - 使用项目根目录作为工作目录
    const pythonProcess = spawn("python", [smsScriptPath], {
      cwd: path.join(__dirname, "..", ".."), // 设置为项目根目录
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
        LANG: "en_US.UTF-8",
      },
    });

    pythonProcess.stdin.write(inputData + "\n");
    pythonProcess.stdin.end();

    let output = "";
    let errorOutput = "";

    // 收集输出 - 添加编码错误处理
    pythonProcess.stdout.on("data", (data) => {
      try {
        output += data.toString("utf8");
      } catch (e) {
        // 如果UTF-8解码失败，尝试其他方式
        output += data.toString();
      }
    });

    pythonProcess.stderr.on("data", (data) => {
      try {
        errorOutput += data.toString("utf8");
      } catch (e) {
        // 如果UTF-8解码失败，尝试其他方式
        errorOutput += data.toString();
      }
    });

    // 等待进程结束
    pythonProcess.on("close", (code) => {
      console.log(`📱 SMS process exited with code: ${code}`);
      console.log("Output:", output);
      console.log("Error output:", errorOutput);

      // 检查是否有明确的成功标识
      const hasSuccessMarker =
        output.includes("SCRIPT_EXIT_SUCCESS") || output.includes("SUCCESS:");
      const hasErrorMarker =
        output.includes("SCRIPT_EXIT_FAILURE") || output.includes("ERROR:");

      if (code === 0 || hasSuccessMarker) {
        // 成功
        res.json({
          success: true,
          message: "SMS sent successfully",
          output: output.trim(),
        });
      } else {
        // 失败 - 改进错误信息处理
        console.error("SMS Error:", errorOutput);
        let errorDetails = errorOutput.trim() || output.trim();

        // 如果错误信息包含乱码，提供更友好的错误信息
        if (
          errorDetails.includes("�") ||
          errorDetails.includes("[MESSAGE_ENCODING_HANDLED]")
        ) {
          errorDetails =
            "SMS sending failed due to encoding issues. Check server logs for details.";
        }

        res.status(500).json({
          success: false,
          error: "SMS sending failed",
          details: errorDetails,
        });
      }
    });

    pythonProcess.on("error", (error) => {
      console.error("SMS Process error:", error);
      res.status(500).json({
        success: false,
        error: "Failed to start SMS process",
        details: error.message,
      });
    });
  } catch (error) {
    console.error("Error sending SMS:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

// 创建单独SMS发送脚本的辅助函数
async function createSingleSmsScript(scriptPath) {
  const scriptContent = `#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import os
import re
import base64
import requests

def safe_print(message):
    try:
        print(str(message))
        sys.stdout.flush()
    except:
        try:
            print(str(message).encode('ascii', 'ignore').decode('ascii'))
            sys.stdout.flush()
        except:
            print("ENCODING_ERROR")
            sys.stdout.flush()

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    safe_print("Firebase Admin SDK not installed")
    sys.exit(1)

class SMSSender:
    def __init__(self):
        self.db = None
        
    def initialize_firebase(self):
        try:
            if not firebase_admin._apps:
                key_paths = [
                    os.path.join(os.path.dirname(__file__), "../../config/firebase/firebase-service-account.json"),
                    "firebase-service-account.json",
                    os.path.join("config", "firebase", "firebase-service-account.json")
                ]
                
                cred = None
                for key_path in key_paths:
                    if os.path.exists(key_path):
                        cred = credentials.Certificate(key_path)
                        break
                
                if cred:
                    firebase_admin.initialize_app(cred)
                else:
                    cred_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
                    if cred_json:
                        cred_dict = json.loads(cred_json)
                        cred = credentials.Certificate(cred_dict)
                        firebase_admin.initialize_app(cred)
                    else:
                        firebase_admin.initialize_app()
            
            self.db = firestore.client()
            return True
        except Exception as e:
            safe_print(f"Firebase init failed: {e}")
            return False
    
    def get_user_config(self, user_uid):
        try:
            doc_ref = self.db.collection('user_configs').document(user_uid)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                return None
        except Exception as e:
            safe_print(f"Get user config failed: {e}")
            return None
    
    def normalize_phone(self, phone):
        digits = re.sub(r'\\\\D', '', phone)
        
        if digits.startswith('81') and len(digits) == 11:
            return '0' + digits[2:]
        elif digits.startswith('81') and len(digits) == 12:
            return '0' + digits[2:]
        elif digits.startswith('0') and len(digits) == 11:
            return digits
        else:
            return digits
    
    def send_sms(self, config, phone, message):
        try:
            sms_config = config.get('sms_config', {})
            
            api_url = sms_config.get('api_url', '')
            api_id = sms_config.get('api_id', '')
            api_password = sms_config.get('api_password', '')
            
            if not all([api_url, api_id, api_password]):
                return False, "SMS API config incomplete"
            
            normalized_phone = self.normalize_phone(phone)
            auth_token = base64.b64encode(f"{api_id}:{api_password}".encode()).decode()
            
            headers = {
                'Authorization': f'Basic {auth_token}',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'SMS-PUBLISHER/1.0'
            }
            
            data = {
                'mobilenumber': normalized_phone,
                'smstext': message.replace('&', '&amp;')
            }
            
            safe_print(f"Sending to: {normalized_phone}")
            safe_print(f"API URL: {api_url}")
            
            response = requests.post(api_url, headers=headers, data=data, timeout=15)
            
            safe_print(f"API Response: {response.status_code}")
            safe_print(f"Response Body: {response.text[:200]}")
            
            if response.status_code == 200:
                response_text = response.text.lower()
                if 'error' in response_text or 'fail' in response_text:
                    return False, f"API returned error: {response.text[:100]}"
                else:
                    return True, "SMS sent successfully"
            else:
                return False, f"API error: {response.status_code} - {response.text[:100]}"
                
        except Exception as e:
            return False, f"SMS send exception: {str(e)}"

def main():
    try:
        input_line = sys.stdin.readline().strip()
        if not input_line:
            safe_print("ERROR: No input data")
            sys.exit(1)
            
        data = json.loads(input_line)
        
        user_uid = data.get('userUid')
        phone = data.get('phone')
        message = data.get('message')
        
        if not all([user_uid, phone, message]):
            safe_print("ERROR: Missing required parameters")
            sys.exit(1)
        
        safe_print(f"Starting SMS send to: {phone}")
        
        sender = SMSSender()
        if not sender.initialize_firebase():
            safe_print("ERROR: Firebase initialization failed")
            sys.exit(1)
        
        config = sender.get_user_config(user_uid)
        if not config:
            safe_print("ERROR: User config not found")
            sys.exit(1)
        
        success, result_message = sender.send_sms(config, phone, message)
        
        if success:
            safe_print(f"SUCCESS: {result_message}")
            sys.exit(0)
        else:
            safe_print(f"ERROR: {result_message}")
            sys.exit(1)
            
    except Exception as e:
        safe_print(f"ERROR: Script execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
`;

  try {
    fs.writeFileSync(scriptPath, scriptContent, "utf8");
    console.log(`✅ Created SMS script: ${scriptPath}`);
  } catch (error) {
    console.error(`❌ Failed to create SMS script: ${error.message}`);
    throw error;
  }
}

// 健康检查
app.get("/api/health", (req, res) => {
  res.json({
    success: true,
    message: "RPA Server is running",
    timestamp: new Date(),
    activeProcesses: rpaProcesses.size,
  });
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`🚀 RPA Server running on http://localhost:${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
});

// 优雅关闭
process.on("SIGINT", () => {
  console.log("\n🛑 Shutting down RPA Server...");

  // 停止所有RPA进程
  for (const [userUid, processInfo] of rpaProcesses) {
    console.log(`  Stopping RPA for user: ${userUid}`);
    processInfo.process.kill("SIGTERM");
  }

  process.exit(0);
});

module.exports = app;

const express = require("express");
const cors = require("cors");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

const app = express();
const PORT = 8888;

// 中间件
app.use(cors());
app.use(express.json());

// 健康检查
app.get("/api/health", (req, res) => {
  res.json({
    status: "OK",
    timestamp: new Date().toISOString(),
    message: "RPA服务器运行正常",
  });
});

// 个人SMS发送API
app.post("/api/sms/send", async (req, res) => {
  try {
    const { userUid, phone, message } = req.body;

    if (!userUid || !phone || !message) {
      return res.status(400).json({
        success: false,
        error: "用户UID、手机号和消息内容都是必需的",
      });
    }

    console.log(`📱 为用户发送SMS: ${userUid}, 发送到: ${phone}`);

    // Python脚本路径
    const smsScriptPath = path.join(
      __dirname,
      "..",
      "rpa",
      "send_personal_sms.py"
    );

    // 检查脚本是否存在
    if (!fs.existsSync(smsScriptPath)) {
      console.log("❌ SMS脚本未找到:", smsScriptPath);
      return res.status(500).json({
        success: false,
        error: "SMS发送脚本未找到",
      });
    }

    // 启动Python进程
    const pythonProcess = spawn("python", [smsScriptPath], {
      cwd: path.join(__dirname, "..", "rpa"),
      stdio: ["pipe", "pipe", "pipe"],
    });

    // 发送输入数据
    const inputData = JSON.stringify({
      userUid: userUid,
      phone: phone,
      message: message,
    });

    pythonProcess.stdin.write(inputData + "\n");
    pythonProcess.stdin.end();

    let output = "";
    let errorOutput = "";

    // 收集输出
    pythonProcess.stdout.on("data", (data) => {
      output += data.toString();
    });

    pythonProcess.stderr.on("data", (data) => {
      errorOutput += data.toString();
    });

    // 处理进程结束
    pythonProcess.on("close", (code) => {
      console.log(`📱 SMS进程退出，代码: ${code}`);
      console.log("输出:", output);

      if (code === 0) {
        // 成功
        res.json({
          success: true,
          message: "SMS发送成功",
          output: output.trim(),
        });
      } else {
        // 失败
        console.error("SMS错误:", errorOutput);
        res.status(500).json({
          success: false,
          error: "SMS发送失败",
          details: errorOutput.trim() || output.trim(),
        });
      }
    });

    pythonProcess.on("error", (error) => {
      console.error("SMS进程错误:", error);
      res.status(500).json({
        success: false,
        error: "无法启动SMS进程",
        details: error.message,
      });
    });
  } catch (error) {
    console.error("SMS API错误:", error);
    res.status(500).json({
      success: false,
      error: "内部服务器错误",
      details: error.message,
    });
  }
});

// RPA执行API
app.post("/api/rpa/start", async (req, res) => {
  try {
    const { userUid, mode } = req.body;

    if (!userUid) {
      return res.status(400).json({
        success: false,
        error: "用户UID是必需的",
      });
    }

    console.log(`🤖 为用户启动RPA: ${userUid}, 模式: ${mode}`);

    // RPA脚本路径
    const rpaScriptPath = path.join(
      __dirname,
      "..",
      "rpa",
      "send_sms_firebase.py"
    );

    // 检查脚本是否存在
    if (!fs.existsSync(rpaScriptPath)) {
      console.log("❌ RPA脚本未找到:", rpaScriptPath);
      return res.status(500).json({
        success: false,
        error: "RPA脚本未找到",
      });
    }

    // 启动Python进程
    const pythonProcess = spawn("python", [rpaScriptPath, userUid], {
      cwd: path.join(__dirname, "..", "rpa"),
      stdio: ["pipe", "pipe", "pipe"],
    });

    let output = "";
    let errorOutput = "";

    // 收集输出
    pythonProcess.stdout.on("data", (data) => {
      output += data.toString();
    });

    pythonProcess.stderr.on("data", (data) => {
      errorOutput += data.toString();
    });

    // 处理进程结束
    pythonProcess.on("close", (code) => {
      console.log(`🤖 RPA进程退出，代码: ${code}`);
      console.log("输出:", output);

      if (code === 0) {
        res.json({
          success: true,
          message: "RPA执行成功",
          output: output.trim(),
        });
      } else {
        console.error("RPA错误:", errorOutput);
        res.status(500).json({
          success: false,
          error: "RPA执行失败",
          details: errorOutput.trim() || output.trim(),
        });
      }
    });

    pythonProcess.on("error", (error) => {
      console.error("RPA进程错误:", error);
      res.status(500).json({
        success: false,
        error: "无法启动RPA进程",
        details: error.message,
      });
    });
  } catch (error) {
    console.error("RPA API错误:", error);
    res.status(500).json({
      success: false,
      error: "内部服务器错误",
      details: error.message,
    });
  }
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`🚀 RPA服务器运行在端口 ${PORT}`);
  console.log(`📡 健康检查: http://localhost:${PORT}/api/health`);
  console.log(`📱 SMS API: http://localhost:${PORT}/api/sms/send`);
  console.log(`🤖 RPA API: http://localhost:${PORT}/api/rpa/start`);
});

module.exports = app;

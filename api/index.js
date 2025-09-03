const express = require("express");
const app = express();

// 中间件
app.use(express.json());

// 健康检查接口
app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    message: "SMS Publisher API is working!",
    timestamp: new Date().toISOString(),
  });
});

// 示例短信发送接口（演示版本）
app.post("/api/sms/send", (req, res) => {
  try {
    const { userUid, phone, message } = req.body;

    // 参数验证
    if (!userUid || !phone || !message) {
      return res.status(400).json({
        success: false,
        error: "缺少必需参数：userUid, phone, message",
      });
    }

    // 模拟发送成功（Demo模式）
    res.json({
      success: true,
      message: "SMS发送成功（Demo模式）",
      data: {
        userUid: userUid,
        phone: phone,
        messagePreview: message.substring(0, 50) + "...",
        timestamp: new Date().toISOString(),
      },
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: "服务器内部错误",
      details: error.message,
    });
  }
});

// 默认路由
app.get("/api", (req, res) => {
  res.json({
    message: "SMS Publisher API服务器运行中",
    endpoints: [
      "GET /api/health - 健康检查",
      "POST /api/sms/send - 发送短信（Demo）",
    ],
  });
});

// 必须导出 app 供 Vercel 识别
module.exports = app;

// Vercel 无服务器函数格式，使用 CommonJS
module.exports = function handler(req, res) {
  // 设置响应头
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Access-Control-Allow-Credentials", true);
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader(
    "Access-Control-Allow-Methods",
    "GET,OPTIONS,PATCH,DELETE,POST,PUT"
  );
  res.setHeader(
    "Access-Control-Allow-Headers",
    "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version"
  );

  // 处理预检请求
  if (req.method === "OPTIONS") {
    res.status(200).end("");
    return;
  }

  const { url, method } = req;

  try {
    // 健康检查接口
    if (
      method === "GET" &&
      (url === "/api/health" || url.endsWith("/health"))
    ) {
      const response = {
        status: "ok",
        message: "SMS Publisher API is working!",
        timestamp: new Date().toISOString(),
      };
      res.status(200).end(JSON.stringify(response));
      return;
    }

    // SMS发送接口
    if (
      method === "POST" &&
      (url === "/api/sms/send" || url.endsWith("/sms/send"))
    ) {
      const { userUid, phone, message } = req.body;

      // 参数验证
      if (!userUid || !phone || !message) {
        const errorResponse = {
          success: false,
          error: "缺少必需参数：userUid, phone, message",
        };
        res.status(400).end(JSON.stringify(errorResponse));
        return;
      }

      // 模拟发送成功（Demo模式）
      const successResponse = {
        success: true,
        message: "SMS发送成功（Demo模式）",
        data: {
          userUid: userUid,
          phone: phone,
          messagePreview: message.substring(0, 50) + "...",
          timestamp: new Date().toISOString(),
        },
      };
      res.status(200).end(JSON.stringify(successResponse));
      return;
    }

    // 默认API路由
    if (
      method === "GET" &&
      (url === "/api" || url === "/" || url.endsWith("/api"))
    ) {
      const defaultResponse = {
        message: "SMS Publisher API服务器运行中",
        endpoints: [
          "GET /api/health - 健康检查",
          "POST /api/sms/send - 发送短信（Demo）",
        ],
      };
      res.status(200).end(JSON.stringify(defaultResponse));
      return;
    }

    // 404 处理
    const notFoundResponse = {
      error: "API endpoint not found",
      url: url,
      method: method,
    };
    res.status(404).end(JSON.stringify(notFoundResponse));
  } catch (error) {
    const errorResponse = {
      success: false,
      error: "服务器内部错误",
      details: error.message,
    };
    res.status(500).end(JSON.stringify(errorResponse));
  }
};

// Vercel 无服务器函数格式
export default function handler(req, res) {
  // 设置 CORS 头
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

  // 处理预检请求
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  const { url, method } = req;

  try {
    // 健康检查接口
    if (method === 'GET' && url === '/api/health') {
      return res.status(200).json({
        status: "ok",
        message: "SMS Publisher API is working!",
        timestamp: new Date().toISOString(),
      });
    }

    // SMS发送接口
    if (method === 'POST' && url === '/api/sms/send') {
      const { userUid, phone, message } = req.body;

      // 参数验证
      if (!userUid || !phone || !message) {
        return res.status(400).json({
          success: false,
          error: "缺少必需参数：userUid, phone, message",
        });
      }

      // 模拟发送成功（Demo模式）
      return res.status(200).json({
        success: true,
        message: "SMS发送成功（Demo模式）",
        data: {
          userUid: userUid,
          phone: phone,
          messagePreview: message.substring(0, 50) + "...",
          timestamp: new Date().toISOString(),
        },
      });
    }

    // 默认API路由
    if (method === 'GET' && (url === '/api' || url === '/')) {
      return res.status(200).json({
        message: "SMS Publisher API服务器运行中",
        endpoints: [
          "GET /api/health - 健康检查",
          "POST /api/sms/send - 发送短信（Demo）",
        ],
      });
    }

    // 404 处理
    return res.status(404).json({
      error: "API endpoint not found",
      url: url,
      method: method
    });

  } catch (error) {
    return res.status(500).json({
      success: false,
      error: "服务器内部错误",
      details: error.message,
    });
  }
}

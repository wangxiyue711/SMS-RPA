const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

// 用于存储任务状态
let taskStatus = new Map();

module.exports = async (req, res) => {
  // 设置CORS头
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
    res.status(200).end();
    return;
  }

  const { method, url: requestUrl } = req;
  const url = requestUrl.split("?")[0]; // 移除查询参数

  try {
    // 健康检查
    if (method === "GET" && url.endsWith("/health")) {
      return res.status(200).json({
        status: "ok",
        message: "SMS Publisher API - Vercel Edition",
        timestamp: new Date().toISOString(),
        environment: "vercel",
      });
    }

    // RPA 任务启动
    if (method === "POST" && url.endsWith("/rpa/start")) {
      const { userUid, mode = "1", interval = 5 } = req.body;

      if (!userUid) {
        return res.status(400).json({
          success: false,
          error: "userUid is required",
        });
      }

      // 在Vercel环境中，我们不能直接运行长时间的进程
      // 这里我们返回一个任务ID并模拟RPA开始
      const taskId = `task_${Date.now()}_${Math.random()
        .toString(36)
        .substr(2, 9)}`;

      taskStatus.set(taskId, {
        userUid,
        mode,
        interval,
        status: "started",
        startTime: new Date().toISOString(),
        lastUpdate: new Date().toISOString(),
      });

      // 在真实环境中，这里应该触发外部RPA服务
      // 例如：调用专门的RPA服务器API，或者加入任务队列

      return res.status(200).json({
        success: true,
        message: "RPA task started",
        taskId: taskId,
        userUid: userUid,
        note: "This is a Vercel demo. In production, this would trigger an external RPA service.",
      });
    }

    // RPA 任务停止
    if (method === "POST" && url.endsWith("/rpa/stop")) {
      const { userUid, taskId } = req.body;

      if (!userUid && !taskId) {
        return res.status(400).json({
          success: false,
          error: "userUid or taskId is required",
        });
      }

      // 查找并停止任务
      let stopped = false;
      for (let [id, task] of taskStatus.entries()) {
        if (
          (taskId && id === taskId) ||
          (userUid && task.userUid === userUid)
        ) {
          task.status = "stopped";
          task.lastUpdate = new Date().toISOString();
          stopped = true;

          if (taskId) break; // 如果指定了taskId，只停止该任务
        }
      }

      return res.status(200).json({
        success: true,
        message: stopped ? "RPA task stopped" : "No running tasks found",
        userUid: userUid,
        taskId: taskId,
      });
    }

    // RPA 任务状态查询
    if (method === "GET" && url.endsWith("/rpa/status")) {
      const { userUid, taskId } = req.query;

      if (!userUid && !taskId) {
        return res.status(400).json({
          success: false,
          error: "userUid or taskId is required",
        });
      }

      const tasks = [];
      for (let [id, task] of taskStatus.entries()) {
        if (
          (taskId && id === taskId) ||
          (userUid && task.userUid === userUid)
        ) {
          tasks.push({
            taskId: id,
            ...task,
          });
        }
      }

      return res.status(200).json({
        success: true,
        tasks: tasks,
        total: tasks.length,
      });
    }

    // SMS 发送接口（Demo）
    if (method === "POST" && url.endsWith("/sms/send")) {
      const { userUid, phone, message, templateType = "default" } = req.body;

      if (!userUid || !phone || !message) {
        return res.status(400).json({
          success: false,
          error: "userUid, phone, and message are required",
        });
      }

      // 在Vercel环境中模拟SMS发送
      // 在生产环境中，这里应该调用真实的SMS服务

      return res.status(200).json({
        success: true,
        message: "SMS sent successfully (Vercel Demo Mode)",
        data: {
          userUid: userUid,
          phone: phone,
          messageLength: message.length,
          templateType: templateType,
          timestamp: new Date().toISOString(),
          provider: "demo",
        },
      });
    }

    // 用户配置管理
    if (method === "POST" && url.endsWith("/config/save")) {
      const { userUid, config } = req.body;

      if (!userUid || !config) {
        return res.status(400).json({
          success: false,
          error: "userUid and config are required",
        });
      }

      // 在真实环境中，这里应该保存到数据库
      // 目前只是返回成功响应
      return res.status(200).json({
        success: true,
        message: "Configuration saved successfully",
        userUid: userUid,
        timestamp: new Date().toISOString(),
      });
    }

    // 获取用户配置
    if (method === "GET" && url.endsWith("/config/get")) {
      const { userUid } = req.query;

      if (!userUid) {
        return res.status(400).json({
          success: false,
          error: "userUid is required",
        });
      }

      // 返回默认配置
      return res.status(200).json({
        success: true,
        config: {
          emailAccount: "",
          emailPassword: "",
          smsTemplate: "",
          intervalSeconds: 5,
          autoStart: false,
        },
        userUid: userUid,
      });
    }

    // 404 处理
    return res.status(404).json({
      success: false,
      error: "Endpoint not found",
      availableEndpoints: [
        "GET /api/health",
        "POST /api/rpa/start",
        "POST /api/rpa/stop",
        "GET /api/rpa/status",
        "POST /api/sms/send",
        "POST /api/config/save",
        "GET /api/config/get",
      ],
    });
  } catch (error) {
    console.error("API Error:", error);
    return res.status(500).json({
      success: false,
      error: "Internal server error",
      message: error.message,
    });
  }
};

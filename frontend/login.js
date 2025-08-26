// This file has been removed as part of the update
// login.js
// 登录按钮无渐变色，成功后跳转到主页面

// 允许的公司ID、邮箱、密码（可自行修改/扩展）
const ALLOWED_USERS = [
  { companyId: "company123", email: "test@example.com", password: "123456" },
  { companyId: "demo", email: "demo@demo.com", password: "demo123" },
];

document.getElementById("loginForm").onsubmit = function (e) {
  e.preventDefault();
  const companyId = document.getElementById("loginCompanyId").value.trim();
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  document.getElementById("loginError").style.display = "none";
  // 校验所有字段
  const user = ALLOWED_USERS.find(
    (u) =>
      u.companyId === companyId && u.email === email && u.password === password
  );
  if (user) {
    localStorage.setItem("companyId", companyId);
    localStorage.setItem("userEmail", email);
    window.location.href = "main_app.html";
  } else {
    document.getElementById("loginError").textContent =
      "会社ID、メールアドレス、またはパスワードが正しくありません。";
    document.getElementById("loginError").style.display = "block";
  }
};

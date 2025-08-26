// This file has been removed as part of the update
// main_app.js
// 左侧菜单共通，按钮切换不同界面
window.onload = function () {
  // 登录信息自动填充
  const companyId = localStorage.getItem("companyId") || "会社名";
  const userEmail = localStorage.getItem("userEmail") || "user@email.com";
  document.getElementById("companyName").textContent = companyId;
  document.getElementById("welcomeCompany").textContent = companyId;
  document.getElementById("userEmail").textContent = userEmail;
  // 默认显示Dashboard
  showPanel("panelDashboard");
  const navs = [
    { btn: "navDashboard", panel: "panelDashboard" },
    { btn: "navSend", panel: "panelSend" },
    { btn: "navConfig", panel: "panelConfig" },
    { btn: "navTeam", panel: "panelTeam" },
    { btn: "navHistory", panel: "panelHistory" },
  ];
  navs.forEach(({ btn, panel }) => {
    document.getElementById(btn).onclick = function () {
      navs.forEach(({ btn: b, panel: p }) => {
        document.getElementById(b).classList.remove("active");
        document.getElementById(p).style.display = "none";
      });
      this.classList.add("active");
      document.getElementById(panel).style.display = "";
    };
  });
};
function showPanel(panelId) {
  const panels = [
    "panelDashboard",
    "panelSend",
    "panelConfig",
    "panelTeam",
    "panelHistory",
  ];
  panels.forEach((pid) => {
    document.getElementById(pid).style.display = pid === panelId ? "" : "none";
  });
  const navs = [
    "navDashboard",
    "navSend",
    "navConfig",
    "navTeam",
    "navHistory",
  ];
  navs.forEach((nid) => {
    document.getElementById(nid).classList.remove("active");
  });
  const navBtn = {
    panelDashboard: "navDashboard",
    panelSend: "navSend",
    panelConfig: "navConfig",
    panelTeam: "navTeam",
    panelHistory: "navHistory",
  }[panelId];
  if (navBtn) document.getElementById(navBtn).classList.add("active");
}

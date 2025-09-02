// Firebase API 管理器 - 多租户架构
import {
  getAuth,
  signInWithEmailAndPassword,
  signOut,
} from "https://www.gstatic.com/firebasejs/9.23.0/firebase-auth.js";
import {
  getFirestore,
  doc,
  getDoc,
  setDoc,
  updateDoc,
} from "https://www.gstatic.com/firebasejs/9.23.0/firebase-firestore.js";

// 等待全局Firebase初始化
function waitForFirebase() {
  return new Promise((resolve) => {
    const checkFirebase = () => {
      if (window.auth && window.db) {
        resolve();
      } else {
        setTimeout(checkFirebase, 100);
      }
    };
    checkFirebase();
  });
}

// 全局状态
window.currentUser = null;
window.currentCompanyId = null;

// 登录管理
async function loginUser(email, password) {
  try {
    console.log("🔥 开始登录流程:", { email });

    await waitForFirebase();
    const auth = window.auth;
    const db = window.db;

    console.log("🔑 尝试Firebase认证...");
    const userCredential = await signInWithEmailAndPassword(
      auth,
      email,
      password
    );
    const user = userCredential.user;

    console.log("✅ Firebase认证成功:", user.uid);

    // 获取用户的公司信息
    console.log("📋 获取用户公司信息...");
    const userDoc = await getDoc(doc(db, "users", user.uid));

    if (!userDoc.exists()) {
      console.log("⚠️ 用户文档不存在，创建默认用户文档");

      // 为新用户创建默认文档
      const defaultUserData = {
        email: user.email,
        company_id: "default_company",
        role: "user",
        created_at: new Date(),
        last_login: new Date(),
      };

      await setDoc(doc(db, "users", user.uid), defaultUserData);

      // 创建默认公司文档
      const defaultCompanyData = {
        name: "デフォルト会社",
        email_config: {
          address: "",
          app_password: "",
        },
        sms_config: {
          provider: "",
          api_key: "",
          api_secret: "",
          endpoint: "",
        },
        templates: {
          default: "こんにちは、メッセージです。",
        },
        created_at: new Date(),
        updated_at: new Date(),
      };

      await setDoc(doc(db, "companies", "default_company"), defaultCompanyData);

      window.currentUser = user;
      window.currentCompanyId = "default_company";

      console.log("✅ 新用户设置完成");
      return {
        success: true,
        user: user,
        companyId: "default_company",
        userData: defaultUserData,
      };
    }

    const userData = userDoc.data();
    window.currentUser = user;
    window.currentCompanyId = userData.company_id;

    console.log("✅ 登录成功:", {
      userId: user.uid,
      companyId: userData.company_id,
    });

    return {
      success: true,
      user: user,
      companyId: userData.company_id,
      userData: userData,
    };
  } catch (error) {
    console.error("❌ 登录失败:", error);

    // 提供更友好的错误信息
    let errorMessage = error.message;

    if (error.code === "auth/user-not-found") {
      errorMessage = "このメールアドレスは登録されていません";
    } else if (error.code === "auth/wrong-password") {
      errorMessage = "パスワードが正しくありません";
    } else if (error.code === "auth/invalid-email") {
      errorMessage = "メールアドレスの形式が正しくありません";
    } else if (error.code === "auth/too-many-requests") {
      errorMessage = "ログイン試行回数が多すぎます。しばらくお待ちください";
    }

    return {
      success: false,
      error: errorMessage,
    };
  }
}

// 登出
async function logoutUser() {
  try {
    await waitForFirebase();
    const auth = window.auth;

    await signOut(auth);
    window.currentUser = null;
    window.currentCompanyId = null;
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// 获取公司配置
async function getCompanyConfig() {
  if (!window.currentCompanyId) {
    throw new Error("ログインが必要です");
  }

  try {
    await waitForFirebase();
    const db = window.db;

    const companyDoc = await getDoc(
      doc(db, "companies", window.currentCompanyId)
    );
    if (companyDoc.exists()) {
      return companyDoc.data();
    } else {
      // 如果公司文档不存在，创建默认配置
      const defaultConfig = {
        name: window.currentCompanyId,
        email_config: {
          address: "",
          app_password: "",
        },
        sms_config: {
          provider: "",
          api_key: "",
          api_secret: "",
          endpoint: "",
        },
        templates: {
          default: "こんにちは、認証コードは{code}です",
        },
        created_at: new Date(),
      };

      await setDoc(
        doc(db, "companies", window.currentCompanyId),
        defaultConfig
      );
      return defaultConfig;
    }
  } catch (error) {
    throw new Error("設定の取得に失敗しました: " + error.message);
  }
}

// 更新邮件配置
async function updateEmailConfig(emailConfig) {
  if (!window.currentCompanyId) {
    throw new Error("ログインが必要です");
  }

  try {
    await waitForFirebase();
    const db = window.db;

    await updateDoc(doc(db, "companies", window.currentCompanyId), {
      email_config: emailConfig,
      updated_at: new Date(),
    });
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// 更新短信配置
async function updateSmsConfig(smsConfig) {
  if (!window.currentCompanyId) {
    throw new Error("ログインが必要です");
  }

  try {
    await waitForFirebase();
    const db = window.db;

    await updateDoc(doc(db, "companies", window.currentCompanyId), {
      sms_config: smsConfig,
      updated_at: new Date(),
    });
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// 导出给全局使用
window.FirebaseAPI = {
  loginUser,
  logoutUser,
  getCompanyConfig,
  updateEmailConfig,
  updateSmsConfig,
};

console.log("Firebase API Manager loaded");

const REQUEST_TIMEOUT_MS = 20000;

const state = {
  sessionId: "",
  threadId: "",
  backendReachable: false,
  creatingSession: false,
  sendingMessage: false,
};

const el = {
  apiBase: document.querySelector("#apiBase"),
  userId: document.querySelector("#userId"),
  createSessionBtn: document.querySelector("#createSessionBtn"),
  sessionInfo: document.querySelector("#sessionInfo"),
  chatLog: document.querySelector("#chatLog"),
  messageInput: document.querySelector("#messageInput"),
  sendBtn: document.querySelector("#sendBtn"),
  planView: document.querySelector("#planView"),
  planJson: document.querySelector("#planJson"),
  appVersion: document.querySelector("#appVersion"),
  buildTime: document.querySelector("#buildTime"),
};

const WEATHER_ICON_MAP = {
  sunny: "☀️",
  cloudy: "⛅",
  overcast: "☁️",
  rain: "🌧️",
  storm: "⛈️",
  snow: "❄️",
  wind: "💨",
  default: "🌤️",
};

const CATEGORY_ICON_MAP = {
  museum: "🏛️",
  culture: "🏮",
  park: "🌿",
  art: "🎨",
  landmark: "📍",
  history: "🧭",
  outdoor: "🌊",
  attraction: "✨",
};

const MEAL_ICON_MAP = {
  breakfast: "🥐",
  lunch: "🍜",
  dinner: "🍽️",
  snack: "☕",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatDateLabel(dateText) {
  if (!dateText) {
    return "日期待定";
  }
  const date = new Date(dateText);
  if (Number.isNaN(date.getTime())) {
    return dateText;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    weekday: "short",
  }).format(date);
}

function classifyWeather(text) {
  const source = String(text || "");
  if (source.includes("雷")) {
    return "storm";
  }
  if (source.includes("雪")) {
    return "snow";
  }
  if (source.includes("雨")) {
    return "rain";
  }
  if (source.includes("阴")) {
    return "overcast";
  }
  if (source.includes("云")) {
    return "cloudy";
  }
  if (source.includes("风")) {
    return "wind";
  }
  if (source.includes("晴")) {
    return "sunny";
  }
  return "default";
}

function weatherIcon(text) {
  return WEATHER_ICON_MAP[classifyWeather(text)] || WEATHER_ICON_MAP.default;
}

function categoryIcon(category) {
  return CATEGORY_ICON_MAP[category] || CATEGORY_ICON_MAP.attraction;
}

function mealIcon(type) {
  return MEAL_ICON_MAP[type] || "🍴";
}

function formatBuildTime(date) {
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(date);
  } catch (_error) {
    return String(date);
  }
}

function bytesToHex(bytes) {
  return Array.from(bytes)
    .map((item) => item.toString(16).padStart(2, "0"))
    .join("");
}

async function computeUiVersion() {
  const url = new URL(import.meta.url);
  const response = await fetch(url.toString(), { method: "GET", cache: "no-store" });
  const source = await response.text();
  const encoder = new TextEncoder();
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(source));
  const hex = bytesToHex(new Uint8Array(digest));
  return `ui-${hex.slice(0, 8)}`;
}

async function detectBuildTime() {
  try {
    const url = new URL(import.meta.url);
    const head = await fetch(url.toString(), { method: "HEAD", cache: "no-store" });
    const lastModified = head.headers.get("last-modified");
    if (lastModified) {
      const dt = new Date(lastModified);
      if (!Number.isNaN(dt.getTime())) {
        return dt;
      }
    }
  } catch (_error) {
    // Ignore and fallback below.
  }

  const documentLastModified = document.lastModified;
  if (documentLastModified) {
    const dt = new Date(documentLastModified);
    if (!Number.isNaN(dt.getTime())) {
      return dt;
    }
  }

  return new Date();
}

async function initBuildInfo() {
  if (!el.appVersion && !el.buildTime) {
    return;
  }

  try {
    const [version, buildTime] = await Promise.all([computeUiVersion(), detectBuildTime()]);

    if (el.appVersion) {
      el.appVersion.textContent = `UI 版本 ${version}`;
    }

    if (el.buildTime) {
      el.buildTime.textContent = `构建时间 ${formatBuildTime(buildTime)}`;
    }
  } catch (error) {
    if (el.appVersion) {
      el.appVersion.textContent = "UI 版本信息不可用";
    }

    if (el.buildTime) {
      el.buildTime.textContent = `构建时间获取失败（${error?.message || "unknown"}）`;
    }
  }
}

function setSessionInfo(text, isError = false) {
  el.sessionInfo.textContent = text;
  el.sessionInfo.style.color = isError ? "#b42318" : "";
}

function updateButtonState() {
  el.createSessionBtn.disabled = state.creatingSession;
  el.sendBtn.disabled = !state.sessionId || state.sendingMessage || !state.backendReachable;
}

function resetSessionState(message) {
  state.sessionId = "";
  state.threadId = "";
  updateButtonState();
  setSessionInfo(message, true);
}

function addMessage(role, text) {
  const item = document.createElement("div");
  item.className = `msg ${role}`;
  item.textContent = `${role === "user" ? "你" : "助手"}: ${text}`;
  el.chatLog.appendChild(item);
  el.chatLog.scrollTop = el.chatLog.scrollHeight;
}

function renderEmptyPlan() {
  el.planView.classList.add("is-empty");
  el.planView.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">🧳</div>
      <h3>暂无规划结果</h3>
      <p>创建会话并发送需求后，这里会展示完整的可视化旅行计划。</p>
    </div>
  `;
  el.planJson.textContent = "{}";
}

function renderWeatherCard(item) {
  const icon = weatherIcon(item.day_weather || item.night_weather);
  return `
    <article class="weather-card">
      <div class="weather-top">
        <div>
          <div class="weather-date">${escapeHtml(formatDateLabel(item.date))}</div>
          <div class="weather-main">${escapeHtml(item.day_weather || item.night_weather || "天气待更新")}</div>
        </div>
        <div class="weather-icon">${icon}</div>
      </div>
      <div class="weather-range">
        <span class="mini-chip">白天 ${escapeHtml(item.day_temp)}°C</span>
        <span class="mini-chip">夜间 ${escapeHtml(item.night_temp)}°C</span>
        <span class="mini-chip">${escapeHtml(item.wind_direction || "风向待定")} ${escapeHtml(item.wind_power || "")}</span>
      </div>
    </article>
  `;
}

function renderAttractionCard(item) {
  const safeName = escapeHtml(item.name || "景点");
  const safeCategory = escapeHtml(item.category || "attraction");
  const safeDescription = escapeHtml(item.description || "暂无描述");
  const safeAddress = escapeHtml(item.address || "地址待补充");
  const imageUrl = escapeHtml(item.image_url || "");

  return `
    <article class="attraction-card">
      <img class="attraction-image" src="${imageUrl}" alt="${safeName}" loading="lazy" />
      <div class="attraction-body">
        <div class="attraction-title-row">
          <h4 class="attraction-title">${categoryIcon(item.category)} ${safeName}</h4>
          <span class="category-chip">${safeCategory}</span>
        </div>
        <p class="attraction-copy">${safeDescription}</p>
        <div class="attraction-meta">
          <span class="meta-chip">⏱️ ${escapeHtml(item.visit_duration)} 分钟</span>
          <span class="meta-chip">🎟️ ${escapeHtml(item.ticket_price || 0)} 元</span>
        </div>
        <div class="meta-note">${safeAddress}</div>
      </div>
    </article>
  `;
}

function renderHotelCard(hotel) {
  if (!hotel) {
    return `
      <div class="hotel-card">
        <div class="hotel-title">
          <h4>🏨 住宿建议</h4>
          <span class="hotel-badge">待确认</span>
        </div>
        <p class="hotel-copy">当前方案还没有明确酒店信息，可以在下一轮继续细化位置和预算。</p>
      </div>
    `;
  }

  return `
    <div class="hotel-card">
      <div class="hotel-title">
        <h4>🏨 ${escapeHtml(hotel.name || "住宿建议")}</h4>
        <span class="hotel-badge">${escapeHtml(hotel.type || "酒店")}</span>
      </div>
      <p class="hotel-copy">${escapeHtml(hotel.address || "地址待补充")}</p>
      <div class="hotel-meta">
        <span class="meta-chip">💰 ${escapeHtml(hotel.price_range || `${hotel.estimated_cost || 0} 元`)}</span>
        <span class="meta-chip">⭐ ${escapeHtml(hotel.rating || "暂无评分")}</span>
        <span class="meta-chip">📍 ${escapeHtml(hotel.distance || "距离待补充")}</span>
      </div>
    </div>
  `;
}

function renderMealCard(item) {
  return `
    <div class="meal-chip">
      <span class="meal-copy-strong">${mealIcon(item.type)} ${escapeHtml(item.name || item.type || "餐饮")}</span>
      <span>${escapeHtml(item.estimated_cost || 0)} 元</span>
    </div>
  `;
}

function renderDayCard(day, weather, index) {
  const dayWeatherText = weather ? weather.day_weather || weather.night_weather : "天气待更新";
  const dayWeatherIcon = weather ? weatherIcon(dayWeatherText) : "🗓️";

  return `
    <article class="day-card" data-day-index="${String(index + 1).padStart(2, "0")}">
      <header class="day-card-header">
        <div class="day-card-top">
          <div>
            <p class="day-kicker">Day ${index + 1}</p>
            <h3 class="day-title">${escapeHtml(day.description || `第 ${index + 1} 天`)}</h3>
            <div class="day-date">${escapeHtml(formatDateLabel(day.date))}</div>
          </div>
          <div class="day-weather-pill">
            <div class="weather-icon">${dayWeatherIcon}</div>
            <div>${escapeHtml(dayWeatherText)}</div>
            <div class="weather-date">${weather ? `${escapeHtml(weather.day_temp)}° / ${escapeHtml(weather.night_temp)}°` : ""}</div>
          </div>
        </div>
        <p class="day-summary">${escapeHtml(day.description || "这一天会围绕核心景点与城市体验展开。")}</p>
        <div class="day-meta-row">
          <span class="transport-chip">🚇 ${escapeHtml(day.transportation || "交通待定")}</span>
          <span class="meta-chip">🛏️ ${escapeHtml(day.accommodation || "住宿待定")}</span>
          <span class="meta-chip">📌 ${escapeHtml((day.attractions || []).length)} 个景点</span>
        </div>
      </header>

      <section class="day-section">
        <div class="section-label">📍 今日景点</div>
        <div class="attraction-grid">
          ${(day.attractions || []).map(renderAttractionCard).join("")}
        </div>
      </section>

      <section class="day-section">
        <div class="section-label">🏨 住宿安排</div>
        ${renderHotelCard(day.hotel)}
      </section>

      <section class="day-section">
        <div class="section-label">🍽️ 餐饮建议</div>
        <div class="meal-grid">
          ${(day.meals || []).map(renderMealCard).join("")}
        </div>
      </section>
    </article>
  `;
}

function renderBudgetCard(budget) {
  const safeBudget = budget || {};
  return `
    <section class="plan-side-card">
      <p class="eyebrow">Budget Check</p>
      <h3>预算总览</h3>
      <div class="budget-grid">
        <div class="budget-item"><span>景点</span><strong>${escapeHtml(safeBudget.total_attractions || 0)} 元</strong></div>
        <div class="budget-item"><span>酒店</span><strong>${escapeHtml(safeBudget.total_hotels || 0)} 元</strong></div>
        <div class="budget-item"><span>餐饮</span><strong>${escapeHtml(safeBudget.total_meals || 0)} 元</strong></div>
        <div class="budget-item"><span>交通</span><strong>${escapeHtml(safeBudget.total_transportation || 0)} 元</strong></div>
        <div class="budget-item total"><span>总计</span><strong>${escapeHtml(safeBudget.total || 0)} 元</strong></div>
      </div>
    </section>
  `;
}

function renderPersonalizationCard(plan) {
  const reasons = plan.personalization_explanation || [];
  const listMarkup = reasons.length
    ? `<ul class="personalization-list">${reasons.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<p>当前计划主要基于你的城市、预算、出行方式和兴趣偏好自动生成。</p>`;

  return `
    <section class="plan-side-card">
      <p class="eyebrow">Why This Plan</p>
      <h3>个性化说明</h3>
      ${listMarkup}
    </section>
  `;
}

function renderPlan(plan) {
  if (!plan) {
    renderEmptyPlan();
    return;
  }

  el.planView.classList.remove("is-empty");
  el.planJson.textContent = JSON.stringify(plan, null, 2);

  const weatherByDate = new Map((plan.weather_info || []).map((item) => [item.date, item]));
  const firstAttraction = plan.days?.[0]?.attractions?.[0];
  const heroImage = firstAttraction?.image_url || "";
  const totalBudget = plan.budget?.total ?? 0;
  const dayCount = (plan.days || []).length;

  el.planView.innerHTML = `
    <section class="plan-hero">
      <img class="plan-hero-image" src="${escapeHtml(heroImage)}" alt="${escapeHtml(plan.city)} 行程封面" loading="lazy" />
      <div class="plan-hero-overlay"></div>
      <div class="plan-hero-content">
        <div>
          <p class="eyebrow">Custom Trip Board</p>
          <h3 class="plan-hero-title">${escapeHtml(plan.city)} ${escapeHtml(dayCount)} 天出行计划</h3>
          <p class="plan-hero-subtitle">${escapeHtml(formatDateLabel(plan.start_date))} - ${escapeHtml(formatDateLabel(plan.end_date))}</p>
        </div>
        <div class="plan-stat-grid">
          <div class="plan-stat"><span class="plan-stat-label">总天数</span><span class="plan-stat-value">${escapeHtml(dayCount)}</span></div>
          <div class="plan-stat"><span class="plan-stat-label">预算</span><span class="plan-stat-value">${escapeHtml(totalBudget)}</span></div>
          <div class="plan-stat"><span class="plan-stat-label">天气</span><span class="plan-stat-value">${weatherIcon(plan.weather_info?.[0]?.day_weather || "")}</span></div>
          <div class="plan-stat"><span class="plan-stat-label">主交通</span><span class="plan-stat-value">${escapeHtml(plan.days?.[0]?.transportation || "待定")}</span></div>
        </div>
        <p class="plan-hero-overview">${escapeHtml(plan.overall_suggestions || "根据你的偏好和预算，系统已为你生成一份结构化的城市探索计划。")}</p>
      </div>
    </section>

    <section class="weather-strip">
      ${(plan.weather_info || []).map(renderWeatherCard).join("")}
    </section>

    <section class="plan-main">
      <div class="day-stack">
        ${(plan.days || []).map((day, index) => renderDayCard(day, weatherByDate.get(day.date), index)).join("")}
      </div>
      <aside class="plan-side">
        ${renderBudgetCard(plan.budget)}
        ${renderPersonalizationCard(plan)}
      </aside>
    </section>
  `;
}

async function requestJson(url, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    const rawText = await response.text();
    let data = null;
    if (rawText) {
      try {
        data = JSON.parse(rawText);
      } catch (_error) {
        data = rawText;
      }
    }

    if (!response.ok) {
      const detail = typeof data === "string" ? data : data?.detail || data?.message || response.statusText;
      throw new Error(detail || `请求失败: ${response.status}`);
    }

    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(`请求超时（>${timeoutMs / 1000} 秒），请检查后端是否正常运行。`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function checkBackendHealth(showMessage = false) {
  const apiBase = el.apiBase.value.trim();
  setSessionInfo("正在检查后端连接...");

  try {
    await requestJson(`${apiBase}/health`, { method: "GET" }, 4000);
    state.backendReachable = true;

    if (state.sessionId) {
      setSessionInfo(`后端已连接 | session_id=${state.sessionId} | thread_id=${state.threadId}`);
    } else {
      setSessionInfo("后端已连接，请先创建会话。");
    }

    if (showMessage) {
      addMessage("assistant", "后端连接正常，可以创建会话了。");
    }
    updateButtonState();
    return true;
  } catch (error) {
    state.backendReachable = false;
    resetSessionState(`后端不可达：${error.message}`);
    if (showMessage) {
      addMessage("assistant", `当前无法连接后端：${error.message}`);
    }
    return false;
  }
}

async function createSession() {
  if (state.creatingSession) {
    return;
  }

  const backendOk = await checkBackendHealth(false);
  if (!backendOk) {
    addMessage("assistant", "创建会话失败：后端当前没有正常响应，请先检查后端服务。");
    return;
  }

  const apiBase = el.apiBase.value.trim();
  const userId = el.userId.value.trim() || "demo_user";

  state.creatingSession = true;
  el.createSessionBtn.textContent = "创建中...";
  updateButtonState();

  try {
    const data = await requestJson(`${apiBase}/api/chat/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });

    state.sessionId = data.session_id;
    state.threadId = data.thread_id;
    state.backendReachable = true;

    setSessionInfo(`会话已创建 | session_id=${data.session_id} | thread_id=${data.thread_id} | user_id=${data.user_id}`);
    addMessage("assistant", "会话创建成功，可以开始描述你的旅行需求。");
  } catch (error) {
    resetSessionState(`创建会话失败：${error.message}`);
    addMessage("assistant", `创建会话失败：${error.message}`);
  } finally {
    state.creatingSession = false;
    el.createSessionBtn.textContent = "创建会话";
    updateButtonState();
  }
}

async function sendMessage() {
  if (!state.sessionId) {
    addMessage("assistant", "请先创建会话。\n如果你已经点过“创建会话”，那通常说明后端没有正常响应。");
    return;
  }

  const message = el.messageInput.value.trim();
  if (!message) {
    return;
  }

  const backendOk = await checkBackendHealth(false);
  if (!backendOk) {
    addMessage("assistant", "消息未发送成功，因为后端当前不可达。请先确认后端服务已正常启动。");
    return;
  }

  const apiBase = el.apiBase.value.trim();
  const userId = el.userId.value.trim() || "demo_user";

  state.sendingMessage = true;
  el.sendBtn.textContent = "发送中...";
  updateButtonState();

  addMessage("user", message);
  el.messageInput.value = "";

  try {
    const data = await requestJson(`${apiBase}/api/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        user_id: userId,
        message,
      }),
    });

    addMessage("assistant", data.assistant_message || "（无回复）");
    renderPlan(data.structured_plan || null);
  } catch (error) {
    addMessage("assistant", `请求失败：${error.message}`);
    if (/session/i.test(error.message)) {
      resetSessionState("会话已失效，请重新创建会话。");
    }
  } finally {
    state.sendingMessage = false;
    el.sendBtn.textContent = "发送";
    updateButtonState();
  }
}

function handleConnectionInputChange() {
  state.backendReachable = false;
  resetSessionState("连接配置已变更，请重新检查后端并创建会话。");
  renderEmptyPlan();
}

el.createSessionBtn.addEventListener("click", async () => {
  await createSession();
});

el.sendBtn.addEventListener("click", async () => {
  await sendMessage();
});

el.apiBase.addEventListener("change", handleConnectionInputChange);
el.userId.addEventListener("change", handleConnectionInputChange);

void initBuildInfo();
updateButtonState();
renderEmptyPlan();
checkBackendHealth(false);

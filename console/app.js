const API = "/api/v1";

const TOKEN_KEY = "ai_company_api_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function requestHeaders() {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
    headers["X-API-Token"] = token;
  }
  return headers;
}

async function api(path, options = {}) {
  let response = await fetch(`${API}${path}`, {
    headers: requestHeaders(),
    ...options,
  });
  if (response.status === 401 && getToken()) {
    // token 可能过期/错误：提示用户重新输入而不是静默失败
    const retry = confirm("当前 API Token 无效（401）。点击确认后重新输入。");
    if (retry) {
      const next = prompt("请输入 API Token：", "");
      if (next !== null) {
        localStorage.setItem(TOKEN_KEY, next.trim());
        response = await fetch(`${API}${path}`, {
          headers: requestHeaders(),
          ...options,
        });
      }
    }
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${detail}`);
  }
  return response.status === 204 ? null : response.json();
}

function statusTag(status) {
  return `<span class="tag ${status}">${status}</span>`;
}

async function loadHealth() {
  const dot = document.getElementById("health-dot");
  const text = document.getElementById("health-text");
  try {
    const data = await api("/health");
    const ok = data.status === "ok";
    dot.className = `dot ${ok ? "ok" : "err"}`;
    text.textContent = `${data.status} · db:${data.database} · redis:${data.redis} · v${data.version}`;
  } catch (error) {
    dot.className = "dot err";
    text.textContent = `不可用：${error.message}`;
  }
}

async function loadAgents() {
  const agents = await api("/agents");
  document.getElementById("agent-list").innerHTML = agents
    .map(
      (agent) => `
      <div class="card">
        <div class="row"><b>${agent.name}</b>${statusTag(agent.status)}</div>
        <div class="muted">${agent.role} · ${agent.domain}</div>
        <div class="muted">skills: ${(agent.skills || []).join(", ") || "-"}</div>
      </div>`
    )
    .join("");
}

async function loadTasks() {
  const tasks = await api("/tasks?limit=30");
  const container = document.getElementById("task-list");
  if (!tasks.length) {
    container.innerHTML = '<div class="muted">暂无任务。</div>';
    return;
  }
  container.innerHTML = tasks
    .map(
      (task) => `
      <div class="card" onclick="showTask('${task.id}')">
        <div class="row"><b>${task.title}</b>${statusTag(task.status)}</div>
        <div class="muted">${task.task_type} · ${task.priority} · ${task.duration_ms ?? "-"} ms</div>
      </div>`
    )
    .join("");
}

window.showTask = async function showTask(taskId) {
  const task = await api(`/tasks/${taskId}`);
  const runs = task.runs || [];
  const steps = runs.length ? runs[runs.length - 1].steps : [];
  const stepHtml = steps
    .map(
      (step) => `
      <div class="step ${step.status}">
        <b>${step.name}</b><span class="tag">${step.status}</span>
        ${step.error ? `<span class="muted">${step.error}</span>` : ""}
      </div>`
    )
    .join("");

  document.getElementById("task-detail").innerHTML = `
    <div class="row"><b>${task.title}</b>${statusTag(task.status)}</div>
    <div class="muted">id: ${task.id} · agent: ${task.assigned_agent_id || "-"} · ${task.duration_ms ?? "-"} ms</div>
    <div class="steps">${stepHtml || '<div class="muted">暂无运行记录</div>'}</div>
    <pre class="result">${(task.result || "暂无结果").replace(/</g, "&lt;")}</pre>
    <div class="evaluate">
      <div class="muted">Pilot 评价（1-5 分）</div>
      <div class="eval-row">
        <label>质量<input id="ev-quality" type="number" min="1" max="5" value="4" /></label>
        <label>体验<input id="ev-experience" type="number" min="1" max="5" value="4" /></label>
        <label>信任<input id="ev-trust" type="number" min="1" max="5" value="3" /></label>
        <label>原耗时(min)<input id="ev-before" type="number" min="0" value="60" /></label>
        <label>AI耗时(min)<input id="ev-after" type="number" min="0" value="10" /></label>
        <label class="inline"><input id="ev-reusable" type="checkbox" /> 愿意复用</label>
        <button onclick="evaluateTask('${task.id}')">提交评价</button>
      </div>
    </div>`;
};

window.evaluateTask = async function evaluateTask(taskId) {
  await api(`/tasks/${taskId}/evaluation`, {
    method: "POST",
    body: JSON.stringify({
      quality: Number(document.getElementById("ev-quality").value),
      experience: Number(document.getElementById("ev-experience").value),
      trust: Number(document.getElementById("ev-trust").value),
      minutes_before: Number(document.getElementById("ev-before").value),
      minutes_after: Number(document.getElementById("ev-after").value),
      reusable: document.getElementById("ev-reusable").checked,
      comment: "",
    }),
  });
  await loadMetrics();
  alert("评价已提交，已计入 Pilot 指标。");
};

async function loadMetrics() {
  const data = await api("/metrics/pilot");
  const items = [
    ["任务总数", data.technical.total_tasks],
    ["成功率", data.technical.task_success_rate],
    ["失败数", data.technical.failed],
    ["平均耗时(ms)", data.technical.average_duration_ms],
    ["评价数", data.ai.evaluations],
    ["结果质量", data.ai.average_quality],
    ["节省时间比", data.ai.average_time_saved_ratio],
    ["愿意复用", data.ai.reusable_ratio],
  ];
  document.getElementById("metrics").innerHTML = items
    .map(([label, value]) => `<div class="metric"><b>${value}</b><span>${label}</span></div>`)
    .join("");
}

const taskTypeSelect = document.querySelector('select[name="task_type"]');
const ecomFields = document.getElementById("ecom-fields");

function updateEcomVisibility() {
  ecomFields.style.display = taskTypeSelect.value === "ecommerce_publish" ? "" : "none";
}

taskTypeSelect.addEventListener("change", updateEcomVisibility);
updateEcomVisibility();

document.getElementById("task-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    title: form.get("title"),
    goal: form.get("goal") || form.get("title"),
    task_type: form.get("task_type"),
    priority: form.get("priority"),
    user_email: form.get("user_email") || null,
    auto_run: true,
  };

  if (taskTypeSelect.value === "ecommerce_publish") {
    const pdir = (form.get("product_dir") || "").trim();
    const mode = form.get("mode") || "draft";
    const acct = (form.get("account") || "").trim() || "default";
    const dry_run = form.get("dry_run") === "on";
    if (!pdir) {
      alert("ecommerce_publish 必须填商品目录，例如 products/DJ-2026-001");
      return;
    }
    payload.input_payload = { product_dir: pdir, mode: mode, account: acct, dry_run: dry_run };
  }
  const button = event.target.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "运行中…";
  try {
    const task = await api("/tasks", { method: "POST", body: JSON.stringify(payload) });
    await loadTasks();
    await loadMetrics();
    await showTask(task.id);
  } catch (error) {
    alert(`提交失败：${error.message}`);
  } finally {
    button.disabled = false;
    button.textContent = "提交并运行";
  }
});

function initTokenUI() {
  const input = document.getElementById("api-token");
  const save = document.getElementById("token-save");
  const clear = document.getElementById("token-clear");
  input.value = getToken();
  save.addEventListener("click", async () => {
    localStorage.setItem(TOKEN_KEY, input.value.trim());
    await loadHealth();
    await Promise.all([loadAgents(), loadTasks(), loadMetrics()]);
    alert(input.value.trim() ? "Token 已保存，接口已带认证。" : "已改为匿名访问。");
  });
  clear.addEventListener("click", async () => {
    localStorage.removeItem(TOKEN_KEY);
    input.value = "";
    await loadHealth();
    await Promise.all([loadAgents(), loadTasks(), loadMetrics()]);
    alert("已清除 Token，接口改为匿名访问。");
  });
}

(async function init() {
  initTokenUI();
  await loadHealth();
  await Promise.all([loadAgents(), loadTasks(), loadMetrics()]);
  setInterval(loadHealth, 30000);
})();

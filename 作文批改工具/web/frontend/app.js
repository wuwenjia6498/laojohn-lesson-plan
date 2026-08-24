/* 老约翰 · 同步习作批改助手 · 前端
 *
 * 三条不要改掉的设计：
 * 1. 逐份**串行**批改，且把已生成的点评卡开头传给下一份（prev_heads）——
 *    一个班二三十份发同一个家长群，句式撞车这工具就废了。并发会让这道防线失效。
 * 2. 图片在本地压到长边 1600 再传：手机原图四五 MB，直传既慢又贵，
 *    而稿纸是黑字白纸、1600 足够认字。
 * 3. 前端不碰密钥。作文分两层，别混成一句「什么都不存」：
 *    **服务端一张不留**——收到即用、用完即弃，不写文件不进日志；
 *    **本机存档**——进老师自己手机的 IndexedDB，不回传。其中又分两种寿命：
 *    **批语永久留**（历史，老师自己在「以前批过的」里删），
 *    **图只留一天**（暂存，为了「批一半被打断能接着批」；一份批完时立刻丢）。
 *    存的是压缩后那张、不是原图。
 */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const S = {
  lessons: [],
  lesson: null,     // 当前课次（精简版标准包）
  items: [],        // 队列：{id, file, blob, url, status, result, error}
  seq: 0,
  sid: "",          // 本次会话号，本机暂存用它认领自己的记录
  busy: false,
  mock: false,
};

const VCLS = { "达成": "v-ok", "部分达成": "v-half", "未达成": "v-no", "不适用": "v-na" };
const BCLS = ["b0", "b1", "b2"];

/* 口令。服务端配了 LJ_ACCESS_CODE 才需要；存在本机，不随批改内容走。 */
const CODE_KEY = "lj_access_code";
const getCode = () => { try { return localStorage.getItem(CODE_KEY) || ""; } catch (e) { return ""; } };
const setCode = (v) => { try { localStorage.setItem(CODE_KEY, v); } catch (e) { /* 无痕模式，本次会话仍可用 */ } };

async function api(path, opts) {
  opts = opts || {};
  const code = getCode();
  if (code) opts.headers = Object.assign({}, opts.headers, { "X-Access-Code": code });
  const r = await fetch(path, opts);
  let d = null;
  try { d = await r.json(); } catch (e) { /* 非 JSON 一律按下面的错处理 */ }
  if (r.status === 401) { const e = new Error((d && d.error) || "口令不对"); e.needCode = true; throw e; }
  if (!r.ok) throw new Error((d && d.error) || `请求失败（${r.status}）`);
  return d;
}

/* ── 视图路由 ───────────────────────────────── */
const VIEWS = ["pick", "grade", "detail", "class", "history"];
let viewStack = ["pick"];

function show(name, title) {
  VIEWS.forEach(v => { $("#view-" + v).hidden = (v !== name); });
  $("#topbar-title").textContent = title || "习作批改";   // 与 manifest 的 short_name 一致
  $("#topbar-title").classList.toggle("dim", name === "pick");
  $("#btn-back").hidden = (name === "pick");
  $("#bottombar").hidden = !(name === "grade" && S.items.length);
  window.scrollTo(0, 0);
}

function go(name, title) {
  if (viewStack[viewStack.length - 1] !== name) viewStack.push(name);
  show(name, title);
}

$("#btn-back").onclick = () => {
  saveFlush();   // 返回是最主要的离开路径，批语可能还在防抖里
  viewStack.pop();
  const back = viewStack[viewStack.length - 1] || "pick";
  if (back === "grade") { show("grade", S.lesson.topic); renderQueue(); }
  else if (back === "pick") {
    viewStack = ["pick"];
    show("pick");
    // 必须重渲：刚选过的那一课要浮到「最近用过」，否则这个区块永远等下次冷启动才出现
    const box = $("#lesson-search");
    if (box) box.value = "";
    if (S.lessons.length) renderLessons("");
  }
  else show(back);
};

$("#btn-info").onclick = () => { $("#sheet-info").hidden = false; };
$("#btn-close-info").onclick = () => { $("#sheet-info").hidden = true; };
$("#sheet-info").onclick = (e) => {
  if (e.target.id === "sheet-info") $("#sheet-info").hidden = true;
};

/* ── 选课 ───────────────────────────────────── */
// 最近用过：老师批一个班是同一课，连着几天多半还是它。这里只存 lesson_id，
// 是本地偏好、常驻不过期。学生数据不进这个 key——它在下面那个 IndexedDB
// 暂存里，24 小时自动清。两者生命周期不同，别混进同一处存储。
const RECENT_KEY = "lj_recent_lessons";
const RECENT_MAX = 2;   // 改这一个数就够——读和写两处都按它截

function getRecent() {
  // 读的时候也截一次：不然把上限调小之后，已经存了更多条的老师要等下次
  // 选课才会被挤掉，改了看着像没生效。
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]").slice(0, RECENT_MAX); }
  catch (e) { return []; }
}

function pushRecent(id) {
  const r = [id, ...getRecent().filter(x => x !== id)].slice(0, RECENT_MAX);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(r)); } catch (e) { /* 隐私模式 */ }
}

/* ── 本机存档（IndexedDB）─────────────────────
 * 一份数据，两个用途，过期策略不同——这是理解这一段的关键：
 *
 *   **批语（result）＝ 历史，永久留**，老师过几天还能打开那一课再看，
 *     只能自己在「以前批过的」里删。一课几十 KB，几十课也不到 1MB。
 *   **图（blob）＝ 暂存，24 小时清**。图只对「重批」和缩略图有用，而重批只对
 *     err 项开放；隔了一天再重批也没意义，而它才是占空间的大头。
 *     一份批完（ok）时立刻丢图，不等 24 小时。
 *
 * 不存什么：原图（存的是 shrink 后的那张，200-500KB）；createObjectURL 的 url
 *   （document 生命周期的，存下来刷新即成死链，只会让缩略图变裂图）。
 * 存在哪：只在老师这台手机的浏览器沙盒里，**不回传服务端**，换手机就没有。
 *   服务端那条「不落盘」红线不受影响——两层是分开的，别混成一句「什么都不存」。
 * 失败怎么办：**一律静默退化成没有存档的行为**。存档是锦上添花，
 *   任何时候都不能挡住批改。
 */
const DB_NAME = "lj_draft", DB_VER = 2;
const BLOB_TTL = 24 * 3600 * 1000;   // 图只留一天；批语不过期，见下
const OFF_KEY = "lj_draft_off";

let dbP = null;        // Promise<IDBDatabase|null>，只解析一次
let dbDead = false;    // 判死开关：一旦为真，所有调用立即返回
let blobsOff = false;  // 配额第一级降级：只停存照片，批语继续存

// 上次在这台设备上探测失败过就别再等那几秒了。但只认 7 天、且 UA 要对得上——
// 老师从微信切到 Safari、或者系统升级了，都该重新给一次机会，不能永久拉黑。
try {
  const off = JSON.parse(localStorage.getItem(OFF_KEY) || "null");
  if (off && off.ua === navigator.userAgent && Date.now() - off.t < 7 * 864e5) dbDead = true;
} catch (e) { /* 隐私模式读不到，就当没记过 */ }

const newSid = () =>
  Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 6);

function markDead() {
  dbDead = true;
  try { localStorage.setItem(OFF_KEY, JSON.stringify({ ua: navigator.userAgent, t: Date.now() })); }
  catch (e) { /* 隐私模式，只好下次再探一遍 */ }
}

function idbOpen() {
  if (dbP) return dbP;
  dbP = new Promise((res) => {
    let done = false;
    const fin = (v) => { if (!done) { done = true; res(v); } };
    // 微信内置浏览器（WKWebView）的失败形态是**挂住不返回**——既不 success
    // 也不 error，所以必须带超时。3 秒是有意放宽的：页面刚加载时事件循环最忙，
    // IDB 回调排在后面，太紧会把「慢」误判成「坏」（idb-probe.html 实测过，
    // 1.5 秒会误杀本机 Chrome）。
    setTimeout(() => fin(null), 3000);
    let req;
    try { req = indexedDB.open(DB_NAME, DB_VER); }
    catch (e) { return fin(null); }   // 部分隐私模式在这里就同步抛了
    req.onupgradeneeded = (ev) => {
      const db = req.result;
      if (!db.objectStoreNames.contains("items")) {
        db.createObjectStore("items", { keyPath: "key" }).createIndex("by_sid", "sid");
      }
      if (!db.objectStoreNames.contains("meta")) db.createObjectStore("meta", { keyPath: "k" });
      // v1 → v2：meta 从「单条会话」改成「每课一条 + 一个当前指针」，结构不兼容。
      // v1 时代的东西本来就只是 24 小时暂存，直接丢掉，不值得写转换。
      if (ev.oldVersion === 1 && req.transaction) {
        try {
          req.transaction.objectStore("meta").clear();
          req.transaction.objectStore("items").clear();
        } catch (e) { /* 清不掉也不影响，下面按 sid 认领时会忽略认不出的记录 */ }
      }
    };
    req.onsuccess = () => fin(req.result);
    req.onerror = req.onblocked = () => fin(null);
  });
  return dbP;
}

/* 全部 IDB 错误的唯一收敛点。签名故意设计成不会 reject——七个调用点一个 try 都不写。 */
async function idbTx(store, mode, fn) {
  if (dbDead) return null;
  try {
    const db = await idbOpen();
    if (!db) { markDead(); return null; }
    return await new Promise((res, rej) => {
      const tx = db.transaction(store, mode);
      const req = fn(tx.objectStore(store));
      tx.oncomplete = () => res(req ? req.result : true);
      // ★ 配额错误落在 tx.error / onabort 上，**不是同步抛的**。只 catch 同步异常，
      //   配额满会变成「静默什么都没存」，连降级都不触发。
      tx.onabort = tx.onerror = () => rej(tx.error || new Error("事务被中止"));
    });
  } catch (e) {
    onIdbFail(e);
    return null;   // 存不下就算了
  }
}

function onIdbFail(e) {
  if (e && e.name === "QuotaExceededError" && !blobsOff) {
    // 两级降级，不一步跳到全关：先只停存照片（批语小得多，通常还存得下）。
    // 优先级写死：**result 必存，blob 尽力**——永远不为了写图把批语挤掉。
    // 只有批语在的那一份，详情页和点评卡照样能用（出图不依赖照片）。
    blobsOff = true;
    return;
  }
  markDead();
}

const recOf = (it) => ({
  key: S.sid + "#" + it.id, sid: S.sid, id: it.id,
  status: it.status, result: it.result, error: it.error,
  blob: (it.status === "ok" || blobsOff) ? null : (it.blob || null),
  ts: Date.now(),
});

function saveItem(it) {
  if (dbDead || !S.sid) return;
  idbTx("items", "readwrite", (s) => s.put(recOf(it)));  // 故意不 await：批改主流程一步都不等本地存储
}

/* 三个编辑框是 oninput，每敲一个字都触发，必须防抖。
   800ms：中文输入法一个词上屏约 300-600ms，再短会退化成「每个词写一次库」；
   再长老师改完一句就可能锁屏。 */
let saveTimer = null, savePend = null;

function saveItemSoon(it) {
  savePend = it;                 // 详情页一次只编辑一份，单槽够用
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => { saveTimer = null; saveItem(savePend); }, 800);
}

// 防抖必须配 flush，否则比不做更坏：老师改完立刻锁屏，恢复出来是旧批语，
// 他会直接不信这个功能。所有离开路径都要 flush。
function saveFlush() {
  if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; saveItem(savePend); }
}

const CUR_KEY = "__cur";   // meta 里指向「当前这一课」的那条

/* 开一课新的。⚠ 不再清库——以前批过的是历史，要留着。 */
function draftReset(lesson) {
  S.sid = newSid();
  if (dbDead) return;
  idbTx("meta", "readwrite", (s) => {
    s.put({ k: CUR_KEY, sid: S.sid });
    s.put({
      k: S.sid, sid: S.sid,
      lesson_id: lesson.lesson_id, lesson_label: lesson.label,
      // mock 必须记：makeCard() 读的是**当前** S.mock。演示模式批的东西，等服务端
      // 配上密钥后再打开，点评卡会不带「非真实批改」水印却带着品牌落款——
      // 那是能发进家长群的对外事故。打开前对不上就不给用。
      mock: S.mock, created: Date.now(), updated: Date.now(), total: 0, done: 0,
    });
  });
}

/* 队列有变动就更新这一课的份数，历史列表要显示它 */
function draftTouch() {
  if (dbDead || !S.sid) return;
  const total = S.items.length;
  const done = S.items.filter(x => x.status === "ok").length;
  idbTx("meta", "readwrite", (s) => {
    const q = s.get(S.sid);
    q.onsuccess = () => {
      const m = q.result;
      if (m) s.put(Object.assign(m, { updated: Date.now(), total, done }));
    };
  });
}

/* 所有批过的课，新的在前。__cur 那条不是课，要滤掉。 */
async function draftSessions() {
  const all = (await idbTx("meta", "readonly", (s) => s.getAll())) || [];
  return all.filter(m => m.k !== CUR_KEY && m.sid)
            .sort((a, b) => (b.updated || 0) - (a.updated || 0));
}

async function draftItems(sid) {
  const all = (await idbTx("items", "readonly", (s) => s.getAll())) || [];
  return all.filter(r => r.sid === sid).sort((a, b) => a.id - b.id);
}

/* 删一课：meta 与它名下的 items 一起走 */
async function draftDropSession(sid) {
  if (dbDead) return;
  const rows = await draftItems(sid);
  idbTx("items", "readwrite", (s) => { rows.forEach(r => s.delete(r.key)); });
  idbTx("meta", "readwrite", (s) => s.delete(sid));
}

function draftClearAll() {
  if (dbDead) return;
  idbTx("items", "readwrite", (s) => s.clear());
  idbTx("meta", "readwrite", (s) => s.clear());
}

/* 图放一天就够了：它只对重批有用，而重批只对 err 项开放，隔天再批也没意义。
   批语不动——那是历史。这一步顺手把占空间的大头清掉，历史却完整保留。 */
async function sweepOldBlobs() {
  if (dbDead) return;
  const all = (await idbTx("items", "readonly", (s) => s.getAll())) || [];
  const old = all.filter(r => r.blob && Date.now() - (r.ts || 0) > BLOB_TTL);
  if (!old.length) return;
  idbTx("items", "readwrite", (s) => {
    old.forEach(r => s.put(Object.assign({}, r, { blob: null })));
  });
}

// blob URL 是 document 生命周期的，不 revoke 就一直钉着内存。以前不补是合理的
// （一个 document 最多泄漏一个班，刷新就回收）；有了「恢复」之后，老师可能在
// 同一个页面里反复恢复、换课、再恢复，那就攒起来了。
// ⚠ 不要在 renderQueue() 里 revoke——<img> 已经引用它，重渲会裂图。
function dropItems() {
  S.items.forEach(it => { if (it.url) { try { URL.revokeObjectURL(it.url); } catch (e) { /* 无所谓 */ } } });
  S.items = [];
  S.seq = 0;
}

/* 口令闸。校验通过前一直不 resolve——外面的 loadLessons 就停在这里，
   不会先把课次列表读出来。口令存本机，下次打开直接过。 */
async function passGate() {
  const check = async () => {
    try { await api("/api/auth-check"); return true; } catch (e) { return false; }
  };
  if (getCode() && await check()) return;

  const gate = $("#gate"), inp = $("#gate-input"), err = $("#gate-err"), btn = $("#gate-go");
  gate.hidden = false;
  inp.focus();
  return new Promise(resolve => {
    const submit = async () => {
      const v = inp.value.trim();
      if (!v || btn.disabled) return;
      btn.disabled = true; err.hidden = true; btn.textContent = "验证中…";
      setCode(v);
      const ok = await check();
      btn.disabled = false; btn.textContent = "进入";
      if (ok) { gate.hidden = true; resolve(); return; }
      setCode("");                       // 存错的会让下次打开还是进不去，且看不出原因
      err.textContent = "口令不对，再试一次";
      err.hidden = false;
      inp.select();
    };
    btn.onclick = submit;
    inp.onkeydown = (e) => { if (e.key === "Enter") submit(); };
  });
}

async function loadLessons() {
  try {
    const h = await api("/api/health");     // health 不要口令，正是用来问「要不要口令」
    S.mock = h.mock;
    if (h.auth) await passGate();           // 拿不到口令就一直停在这，不往下走
    S.lessons = await api("/api/lessons");
  } catch (e) {
    $("#lesson-list").innerHTML = `<p class="hint">读不到课次：${esc(e.message)}</p>`;
    return;
  }
  const box = $("#lesson-search");
  box.hidden = S.lessons.length < 8;      // 课次少时搜索框只是碍事
  box.oninput = () => renderLessons(box.value.trim());
  renderLessons("");
}

function lessonCard(l) {
  return `<button class="lesson" data-id="${esc(l.lesson_id)}">
      <div class="t">${esc(l.label)}</div>
      <div class="s">${esc(l.core_technique)}</div>
      <span class="tag${l.verified ? "" : " unverified"}">${
        l.verified ? "判据已核" : "判据待人工核对"}</span>
    </button>`;
}

// 展开哪几册。第一次渲染时定：优先展开最近用过那一册，否则第一册。
let openGrades = null;

function renderLessons(kw) {
  const all = S.lessons;
  const list = kw
    ? all.filter(l => (l.label + l.topic + l.core_technique).includes(kw))
    : all;

  const groups = [];
  for (const l of list) {
    const g = groups.find(x => x.key === l.grade_key);
    if (g) g.items.push(l);
    else groups.push({ key: l.grade_key, label: l.grade_label, items: [l] });
  }

  const recentIds = getRecent().filter(id => list.some(l => l.lesson_id === id));
  if (openGrades === null) {
    const first = recentIds.length
      ? (all.find(l => l.lesson_id === recentIds[0]) || {}).grade_key
      : (groups[0] || {}).key;
    openGrades = new Set(first ? [first] : []);
  }

  // 课次少、或只有一册时不分组——两课还摆个折叠面板，是给自己加戏
  const flat = kw || list.length <= 6 || groups.length <= 1;

  let html = "";
  if (!list.length) {
    html = `<p class="hint">没有匹配的课次。</p>`;
  } else if (flat) {
    html = list.map(lessonCard).join("");
  } else {
    if (recentIds.length) {
      html += `<div class="grouphead plain">最近用过</div>`
            + recentIds.map(id => lessonCard(all.find(l => l.lesson_id === id))).join("");
    }
    html += groups.map(g => {
      const open = openGrades.has(g.key);
      return `<button class="grouphead" data-g="${esc(g.key)}">
          <span class="gt">${esc(g.label)}</span>
          <span class="gn">${g.items.length} 课</span>
          <span class="gc${open ? " open" : ""}">›</span>
        </button>` + (open ? g.items.map(lessonCard).join("") : "");
    }).join("");
  }
  $("#lesson-list").innerHTML = html;

  $$("#lesson-list .lesson").forEach(b => {
    b.onclick = () => pickLesson(S.lessons.find(l => l.lesson_id === b.dataset.id));
  });
  $$("#lesson-list .grouphead[data-g]").forEach(b => {
    b.onclick = () => {
      const k = b.dataset.g;
      openGrades.has(k) ? openGrades.delete(k) : openGrades.add(k);
      renderLessons(kw);
    };
  });
}

/* 通用询问框。不用 confirm()：微信内置浏览器的 confirm 会带上域名标题，风格不搭，
   而且能被「阻止此页面再弹出」永久屏蔽——那会让恢复入口凭空消失。 */
function askSheet(title, html, okText, cancelText) {
  return new Promise((res) => {
    $("#ask-title").textContent = title;
    $("#ask-body").innerHTML = html;
    const ok = $("#btn-ask-ok"), no = $("#btn-ask-no");
    ok.textContent = okText; no.textContent = cancelText;
    const done = (v) => { $("#sheet-ask").hidden = true; ok.onclick = no.onclick = null; res(v); };
    ok.onclick = () => done(true);
    no.onclick = () => done(false);
    $("#sheet-ask").hidden = false;
  });
}

async function pickLesson(l) {
  // 换课会清掉队列。ok 那几份是花过真钱和时间换来的，而且没有任何副本——点评卡
  // 要长按保存才落地，老师十有八九还没导出。而「返回选课页看一眼再点回来」是
  // 完全正常的路径，手指离另一课的按钮只有几十像素。加了暂存之后性质变了：
  // 「我明明存下来了却被一次误触清掉」比「刷新就没了」更让人恼火。
  const kept = S.items.filter(x => x.status === "ok").length;
  if (kept && S.lesson && l.lesson_id !== S.lesson.lesson_id) {
    // askSheet 的第一个按钮永远是安全的那个，所以这里问的是「留下」
    const stay = await askSheet(
      "换课会清掉上一课",
      esc(S.lesson.label) + " 还有 <b>" + kept + " 份</b>批完了没导出，换过去就清掉了。",
      "先回去导出", "还是换课");
    if (stay) return;
  }
  S.lesson = l;
  dropItems();
  draftReset(l);
  pushRecent(l.lesson_id);
  renderBrief();
  renderQueue();
  go("grade", l.topic);
}

function renderBrief() {
  const l = S.lesson;
  $("#lesson-brief").innerHTML = `
    ${S.mock ? '<div class="mockbar">演示模式：服务端没配密钥，下面的批改结果是<b>假数据</b>，只用来看流程。</div>' : ""}
    <h2>${esc(l.label)}</h2>
    <div class="hint">${esc(l.core_technique)}</div>
    <ul class="checks">
      ${l.three_checks.map(c => `<li><span>${c.no}</span>${esc(c.text)}</li>`).join("")}
    </ul>
    <div class="nis">不看：${esc(l.not_in_scope.join("、"))}——这一层交给你当面看稿。</div>`;
}

/* ── 图片压缩 ───────────────────────────────── */
async function shrink(file, maxSide = 1600, quality = 0.82) {
  try {
    const bmp = await createImageBitmap(file);
    const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
    const w = Math.round(bmp.width * scale), h = Math.round(bmp.height * scale);
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    cv.getContext("2d").drawImage(bmp, 0, 0, w, h);
    bmp.close && bmp.close();
    const blob = await new Promise(res => cv.toBlob(res, "image/jpeg", quality));
    return blob || file;
  } catch (e) {
    // createImageBitmap 在旧 iOS 上遇 HEIC 或超大图会抛错。原样发出去：
    // 四五 MB 可能撞服务端的 8MB 上限，但那时错误信息是明确的（服务端会说图太大），
    // 比在这儿抛一句 createImageBitmap 的内部错误强得多。
    return file;
  }
}

/* ── 队列 ───────────────────────────────────── */
$("#file-input").onchange = (e) => {
  const files = [...e.target.files];
  e.target.value = "";
  if (!files.length) return;
  files.forEach(f => {
    const it = {
      id: ++S.seq, file: f, blob: null, url: URL.createObjectURL(f),
      status: "wait", result: null, error: "",
    };
    S.items.push(it);
    // 先写一条没有图的占位。一次导入三十张、手机在第三张就被杀掉时，
    // 份数和顺序不会丢，恢复框能说出真实的数字。图等压缩完再补（见 pump）。
    saveItem(it);
  });
  renderQueue();
  draftTouch();
  pump();
};

function statusCell(it) {
  if (it.status === "wait") return '<span class="badge wait">排队中</span>';
  if (it.status === "run") return '<span class="spin"></span>';
  if (it.status === "err") return '<span class="badge err">失败·点开重试</span>';
  const r = it.result, bi = S.lesson.bands.indexOf(r.band);
  return `<span class="badge ${BCLS[bi] || "b1"}">${esc(r.band)}</span>`;
}

function renderQueue() {
  const q = $("#queue");
  $("#empty-tip").hidden = S.items.length > 0;
  q.innerHTML = S.items.map(it => {
    const r = it.result;
    const name = r && r.student_name ? esc(r.student_name)
      : `<span class="anon">第 ${it.id} 份（没读到姓名）</span>`;
    const sub = it.status === "err" ? esc(it.error)
      : (r ? esc(r.focus || r.teacher_note || "") : "等着批…");
    return `<button class="card" data-id="${it.id}">
      ${it.url ? `<img class="thumb" src="${it.url}" alt="">`
              : `<span class="thumb ph">照片<br>没存</span>`}
      <div class="mid"><div class="name">${name}</div><div class="sub">${sub}</div></div>
      ${statusCell(it)}
      <span class="go">›</span>
    </button>`;
  }).join("");
  $$("#queue .card").forEach(b => {
    b.onclick = () => openDetail(S.items.find(x => x.id === +b.dataset.id));
  });
  // 暂存的图万一坏了（写到一半被杀、存储层出错），<img> 会显示成裂图——那看起来
  // 像整个工具坏了。换成和「照片没存」一样的占位块，批语该怎么用还怎么用。
  $$("#queue img.thumb").forEach(img => {
    img.onerror = () => {
      const ph = document.createElement("span");
      ph.className = "thumb ph";
      ph.innerHTML = "照片<br>坏了";
      img.replaceWith(ph);
    };
  });
  const done = S.items.filter(x => x.status === "ok").length;
  $("#bottom-stat").textContent = S.items.length
    ? `已批 ${done} / ${S.items.length} 份` : "";
  $("#btn-class").disabled = done === 0;
  $("#bottombar").hidden = !S.items.length || $("#view-grade").hidden;
}

/* 串行泵：一份批完再批下一份，并把已有的点评卡开头带给下一份 */
async function pump() {
  if (S.busy) return;
  S.busy = true;
  try {
    while (true) {
      const it = S.items.find(x => x.status === "wait");
      if (!it) break;
      // run 这一步**有意不写库**：库里留着 wait + 已经压好的图，进程被杀后恢复，
      // 它自然回到待批队列——那正是「接着批」要的。写 run 反而要在恢复时降级回 wait。
      it.status = "run"; renderQueue();
      try {
        // 压缩产物过去是临时的、用完即扔。现在回写进 it.blob 再落盘，顺手解决三件事：
        // ① 重批不再二次压缩（q0.82 压两遍，手写的细笔画会发糊——这是识别率问题）；
        // ② 恢复出来的项天生带图，不必再去碰已经不存在的原图；
        // ③ 图在**发起网络请求之前**就落了盘，所以「传到一半被杀」留下的是一条
        //    可以直接重批的完整记录。
        // ⚠ 守卫必须写 !it.blob，**不能写 it.file**——恢复出来的项 file 是 null，
        //    写反了就是 shrink(null)。
        if (!it.blob) { it.blob = await shrink(it.file); saveItem(it); }
        const fd = new FormData();
        fd.append("lesson_id", S.lesson.lesson_id);
        fd.append("prev_heads", JSON.stringify(
          S.items.filter(x => x.result && x.result.parent_card)
                 .map(x => x.result.parent_card.slice(0, 24))));
        fd.append("image", it.blob, "sheet.jpg");
        it.result = await api("/api/grade", { method: "POST", body: fd });
        it.status = "ok";
      } catch (e) {
        it.status = "err"; it.error = e.message;
      }
      saveItem(it);   // ok 时 recOf 会顺手把图丢掉，err 时保住错误文案
      draftTouch();
      renderQueue();
    }
  } finally { S.busy = false; }
}

/* ── 单份详情 ───────────────────────────────── */
let cur = null;

function openDetail(it) {
  saveFlush();   // 上一份的批语可能还在防抖里等着，单槽会被这一份覆盖
  cur = it;
  if (it.status === "err") {
    // 图没存下来的那种 err 批不动：转 wait → pump → !it.blob 成立 → shrink(null)
    // → 又回 err，会一直空转。直接说清楚要重拍。
    if (!it.blob && !it.file) {
      it.error = "照片没能存下来，请重新拍这一份";
      renderQueue();
      return;
    }
    it.status = "wait"; it.error = "";
    saveItem(it);
    renderQueue(); pump();
    return;
  }
  if (it.status !== "ok") return;
  renderDetail();
  go("detail", (it.result.student_name || "这一份") + " · 批改");
}

const WP_ROWS = [
  ["completeness", "写完了没有"],
  ["order", "顺序清不清楚"],
  ["flow", "句子顺不顺"],
];
// 整篇三项的判定分好坏两色。三项**不进档位**（档位只由三条判据定），
// 这里只给老师看，也不要把「逻辑乱」这种话直接转给家长。
const WP_BAD = ["没写完", "只开了个头", "有跳跃", "乱", "个别别扭", "多处不通"];

function renderDetail() {
  const it = cur, r = it.result, l = S.lesson;
  const checkMap = Object.fromEntries(l.three_checks.map(c => [c.no, c.text]));

  const focus = r.focus ? `<div class="focus"><b>这一篇最值得说的</b>${esc(r.focus)}</div>` : "";

  const hls = r.highlights || [];
  const hlBody = hls.length
    ? hls.map(h => `<div class="hl">
        <div class="q${h.quote_suspect ? " sus" : ""}">${esc(h.quote)}${
          h.quote_suspect ? '<span class="sustag">与原文对不上，核一下</span>' : ""}</div>
        <div class="w">${h.kind ? `<span class="kind">${esc(h.kind)}</span>` : ""}${esc(h.why)}</div>
      </div>`).join("")
    : `<div class="hint">这一篇没有特别出彩的句子。<b>不用硬找</b>——硬夸家长看得出来。</div>`;

  const wp = r.whole_piece || {};
  const wpBody = WP_ROWS.map(([k, label]) => {
    const v = wp[k] || {};
    const bad = WP_BAD.includes(v.verdict);
    return `<div class="wp">
      <div class="h"><span class="t">${label}</span>
        <span class="v ${bad ? "v-no" : "v-ok"}">${esc(v.verdict || "—")}</span></div>
      ${v.note ? `<div class="cm">${esc(v.note)}</div>` : ""}
      ${bad && v.evidence ? `<div class="ev sm">${esc(v.evidence)}</div>` : ""}
    </div>`;
  }).join("");

  const checks = (r.checks || []).map(c => `
    <div class="check">
      <div class="h">
        <span class="no">${c.no}</span>
        <span class="t">${esc(checkMap[c.no] || "")}</span>
        <span class="v ${VCLS[c.verdict] || ""}">${esc(c.verdict)}</span>
      </div>
      ${c.evidence ? `<div class="ev${c.evidence_suspect ? " sus" : ""}">${esc(c.evidence)}${
        c.evidence_suspect ? '<span class="sustag">与原文对不上，核一下</span>' : ""}</div>` : ""}
      ${c.comment ? `<div class="cm">${esc(c.comment)}</div>` : ""}
    </div>`).join("");

  const unclear = (r.unclear || []).length ? `
    <div class="unclear"><b>这几处它没看清，你翻原稿确认一下</b>
      ${r.unclear.map(u => `<div>· ${esc(u)}</div>`).join("")}</div>` : "";

  const sc = r.showcase || {};
  const showcase = sc.suitable ? `
    <div class="sec">
      <h3>可以拿到讲评课上念<span class="aside">讲：${esc(sc.point || "")}</span></h3>
      <div class="ev">${esc(sc.paragraph || "")}</div>
    </div>` : "";
  $("#detail-body").innerHTML = `
    <div class="namerow">
      <input id="in-name" value="${esc(r.student_name || "")}" placeholder="没读到姓名，手填">
      <span class="badge ${BCLS[l.bands.indexOf(r.band)] || "b1"}">${esc(r.band)}</span>
    </div>
    ${focus}
    ${unclear}
    <div class="sec">
      <h3>他自己写得好的地方<span class="aside">点评卡优先引这里的句子</span></h3>
      ${hlBody}
    </div>
    <div class="sec"><h3>三条判据<span class="aside">学生课上听过这三条</span></h3>${checks}</div>
    <div class="sec">
      <h3>整篇怎么样<span class="aside">不算档位，给你参考</span></h3>${wpBody}
    </div>
    <div class="sec">
      <h3>写进稿纸「老师批改」栏<span class="aside">30 字以内</span></h3>
      <textarea id="ta-note" rows="2">${esc(r.teacher_note || "")}</textarea>
      <div class="row"><button class="ghost" id="btn-copy-note">复制这句</button></div>
    </div>
    ${showcase}
    <div class="sec">
      <h3>给家长的点评卡<span class="aside">改完再出图</span></h3>
      ${r.quoted_sentence_suspect ? `<div class="unclear"><b>点评卡引的那句话，跟稿纸对不上</b>
        它引的是：${esc(r.quoted_sentence || "")}<br>发出去之前请对着原稿核一遍。</div>` : ""}
      <textarea id="ta-card" rows="7">${esc(r.parent_card || "")}</textarea>
      <div class="count" id="cnt-card"></div>
      <div class="row">
        <button class="ghost" id="btn-copy-card">复制文字</button>
        <button class="primary" id="btn-make">生成图片</button>
      </div>
      <img id="cardimg" hidden alt="点评卡">
      <div class="saveTip" id="save-tip" hidden>长按上面这张图保存，再发到家长群。</div>
    </div>`;

  const ta = $("#ta-card"), cnt = $("#cnt-card");
  const upd = () => {
    const n = ta.value.trim().length;
    cnt.textContent = `${n} 字`;
    cnt.classList.toggle("over", n > 160);
  };
  ta.oninput = () => { cur.result.parent_card = ta.value; upd(); saveItemSoon(cur); };
  upd();
  $("#in-name").oninput = (e) => { cur.result.student_name = e.target.value; saveItemSoon(cur); };
  $("#ta-note").oninput = (e) => { cur.result.teacher_note = e.target.value; saveItemSoon(cur); };
  $("#btn-copy-note").onclick = () => copy($("#ta-note").value, $("#btn-copy-note"));
  $("#btn-copy-card").onclick = () => copy(ta.value, $("#btn-copy-card"));
  $("#btn-make").onclick = makeCard;
}

async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); }
  catch (e) {
    const t = document.createElement("textarea");
    t.value = text; document.body.appendChild(t); t.select();
    document.execCommand("copy"); t.remove();
  }
  const old = btn.textContent;
  btn.textContent = "已复制";
  setTimeout(() => { btn.textContent = old; }, 1200);
}

/* ── 点评卡出图（canvas，前端画，长按保存）───── */
const CARD_W = 750, PAD = 56;
const FONT = '"PingFang SC","Microsoft YaHei","Hiragino Sans GB",sans-serif';

// 行首禁则：这些字符不许被挤到下一行开头（中文排版的避头尾），
// 宁可让上一行稍微出头一点。发到家长群的图，标点吊在行首一眼就露怯。
// 只收窄标点：全角的 —— …… 挤出去有两个字宽，会冲破卡片边距。
const NO_LINE_START = "，。、；：？！）》」』”’·%";
const NO_LINE_END = "（《「『“‘";

// 成对的破折号与省略号是一个整体，拆开断行是中文排版硬伤——先并成一个 token
function tokenize(para) {
  const cs = [...para], out = [];
  for (let i = 0; i < cs.length; i++) {
    if ((cs[i] === "—" || cs[i] === "…") && cs[i + 1] === cs[i]) { out.push(cs[i] + cs[i]); i++; }
    else out.push(cs[i]);
  }
  return out;
}

function wrap(ctx, text, maxW) {
  const lines = [];
  for (const para of String(text).split(/\n+/)) {
    let line = "";
    for (const tk of tokenize(para)) {
      const over = ctx.measureText(line + tk).width > maxW && line;
      if (over && NO_LINE_START.includes(tk)) { line += tk; continue; }
      if (over) {
        const last = line[line.length - 1];
        if (NO_LINE_END.includes(last) && line.length > 1) {
          // 开引号一类不能留在行尾，跟着下一个字一起挪到下一行
          lines.push(line.slice(0, -1)); line = last + tk;
        } else { lines.push(line); line = tk; }
      } else line += tk;
    }
    if (line) lines.push(line);
  }
  return lines;
}

function makeCard() {
  const r = cur.result, l = S.lesson;
  const body = ($("#ta-card").value || "").trim();
  const innerW = CARD_W - PAD * 2;

  const probe = document.createElement("canvas").getContext("2d");
  probe.font = `30px ${FONT}`;
  const lines = wrap(probe, body, innerW);

  const yBody = 246;          // 第一行文字的基线
  const lh = 54;
  // 末行基线到卡片底边留 128：算成 lines.length*lh 会多出一整行的空，底部发虚
  const H = yBody + (lines.length - 1) * lh + 128;

  const cv = document.createElement("canvas");
  cv.width = CARD_W; cv.height = H;
  const c = cv.getContext("2d");

  c.fillStyle = "#FFFFFF"; c.fillRect(0, 0, CARD_W, H);
  c.fillStyle = "#C8352B"; c.fillRect(0, 0, CARD_W, 10);

  // 演示模式：卡片本身必须自带「假」的标记。这张图的用途就是被转发出去，
  // 一张内容全假、却带着品牌落款的点评卡流到家长手里，比界面上少一句提示严重得多。
  // 水印先画，正文压在它上面，不影响可读性。
  if (S.mock) {
    c.save();
    c.translate(CARD_W / 2, H / 2);
    c.rotate(-Math.PI / 9);
    c.fillStyle = "rgba(200,53,43,.075)";
    c.font = `700 86px ${FONT}`;
    c.textAlign = "center";
    c.fillText("非真实批改", 0, 0);
    c.restore();
  }

  c.fillStyle = "#C8352B"; c.font = `600 24px ${FONT}`;
  c.fillText("老约翰 · 同步习作", PAD, 84);

  if (S.mock) {
    const tag = "演示样张";
    c.font = `600 22px ${FONT}`;
    const tw = c.measureText(tag).width, bw = tw + 28, bx = CARD_W - PAD - bw, by = 58;
    c.fillStyle = "#FBEAE8";
    c.beginPath();
    if (c.roundRect) c.roundRect(bx, by, bw, 38, 19); else c.rect(bx, by, bw, 38);
    c.fill();
    c.fillStyle = "#C8352B";
    c.fillText(tag, bx + 14, by + 27);
  }

  c.fillStyle = "#3A3A38"; c.font = `700 46px ${FONT}`;
  c.fillText("作文点评", PAD, 146);

  c.fillStyle = "#7A7568"; c.font = `24px ${FONT}`;
  const who = (r.student_name || "").trim();
  c.fillText(`${who ? who + "　·　" : ""}${l.label}`, PAD, 190);

  c.strokeStyle = "#E3DED4"; c.lineWidth = 1;
  c.beginPath(); c.moveTo(PAD, 214); c.lineTo(CARD_W - PAD, 214); c.stroke();

  c.fillStyle = "#3A3A38"; c.font = `30px ${FONT}`;
  lines.forEach((t, i) => c.fillText(t, PAD, yBody + i * lh));

  const yFoot = H - 62;
  c.strokeStyle = "#E3DED4";
  c.beginPath(); c.moveTo(PAD, yFoot); c.lineTo(CARD_W - PAD, yFoot); c.stroke();
  c.fillStyle = "#A89B8A"; c.font = `22px ${FONT}`;
  c.fillText(S.mock ? "演示用样张 · 非真实学生作品"
                    : "老约翰深度阅读 · 写清楚 写生动 有章法", PAD, yFoot + 38);
  const d = new Date();
  const ds = `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
  c.textAlign = "right"; c.fillText(ds, CARD_W - PAD, yFoot + 38);

  const img = $("#cardimg");
  img.src = cv.toDataURL("image/jpeg", 0.92);
  img.hidden = false;
  $("#save-tip").hidden = false;
  img.scrollIntoView({ behavior: "smooth", block: "center" });
}

/* ── 班级诊断 ───────────────────────────────── */
$("#btn-class").onclick = async () => {
  const done = S.items.filter(x => x.status === "ok").map(x => x.result);
  if (!done.length) return;
  go("class", "班级诊断");
  const counts = S.lesson.bands.map(b => done.filter(r => r.band === b).length);
  $("#class-body").innerHTML = `
    <div class="stats">
      <div class="stat"><b>${done.length}</b><span>已批</span></div>
      ${S.lesson.bands.map((b, i) =>
        `<div class="stat"><b>${counts[i]}</b><span>${esc(b)}</span></div>`).join("")}
    </div>
    <div class="sec"><h3>正在看这一批的共性…</h3><div class="hint">稍等几秒。</div></div>`;

  let d;
  try {
    d = await api("/api/diagnose", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lesson_id: S.lesson.lesson_id, results: done }),
    });
  } catch (e) {
    $("#class-body").insertAdjacentHTML("beforeend",
      `<div class="sec"><h3>没出来</h3><div class="hint">${esc(e.message)}</div></div>`);
    return;
  }

  const probs = (d.common_problems || []).map(p => `
    <div class="prob">
      <div class="p">${p.layer ? `<span class="layer ${p.layer === "整篇" ? "l2" : "l1"}">${esc(p.layer)}</span>` : ""}${esc(p.problem)}</div>
      <div class="m">${esc(p.how_many || "")}　${esc(p.why || "")}</div>
      <div class="f">讲评课上：${esc(p.how_to_fix || "")}</div>
    </div>`).join("");

  const plan = (d.showcase_plan || []).map(s => `
    <div class="prob">
      <div class="p">${esc(s.name || "")}</div>
      <div class="m">念：${esc(s.read_what || "")}</div>
      <div class="f">用来讲：${esc(s.teach_what || "")}</div>
    </div>`).join("");

  $("#class-body").innerHTML = `
    <div class="stats">
      <div class="stat"><b>${done.length}</b><span>已批</span></div>
      ${S.lesson.bands.map((b, i) =>
        `<div class="stat"><b>${counts[i]}</b><span>${esc(b)}</span></div>`).join("")}
    </div>
    <div class="sec"><h3>整体</h3><div>${esc(d.overall || "")}</div></div>
    ${d.whole_piece_summary ? `<div class="sec">
      <h3>地基这一层<span class="aside">比本课技法更该先管</span></h3>
      <div>${esc(d.whole_piece_summary)}</div></div>` : ""}
    ${probs ? `<div class="sec"><h3>共性问题</h3>${probs}</div>` : ""}
    ${plan ? `<div class="sec"><h3>讲评课念谁的</h3>${plan}</div>` : ""}
    ${d.next_lesson_slots ? `<div class="sec">
      <h3>填进详案讲评环节的空槽<span class="aside">可直接抄</span></h3>
      <textarea id="ta-slot" rows="5">${esc(d.next_lesson_slots)}</textarea>
      <div class="row"><button class="ghost" id="btn-copy-slot">复制</button></div>
    </div>` : ""}`;

  const b = $("#btn-copy-slot");
  if (b) b.onclick = () => copy($("#ta-slot").value, b);
};

/* ── 启动时的暂存恢复 ─────────────────────────── */
async function draftBoot(lessonsP) {
  if (dbDead) return;
  sweepOldBlobs();            // 顺手把过夜的图清掉，历史（批语）不动

  const cur = await idbTx("meta", "readonly", (s) => s.get(CUR_KEY));
  if (!cur || !cur.sid) { refreshHist(); return; }
  const meta = await idbTx("meta", "readonly", (s) => s.get(cur.sid));
  if (!meta) { refreshHist(); return; }

  // loadLessons 内部自己 catch 了、永远 resolve，所以判失败要看 S.lessons 有没有货。
  // ⚠ 网络抽风时**不弹框、也绝不删任何东西**。同时这一步保证 S.mock 已经是真的。
  await lessonsP;
  refreshHist();
  if (!S.lessons.length) return;

  // 演示模式批的东西在真实模式下一文不值，反过来也一样（makeCard 读的是当前
  // S.mock，拿演示稿出图会少掉「非真实批改」水印却带着品牌落款）。不打扰，
  // 但也不删——它照样躺在历史里，从那边打开时会被拦住。
  if (!!meta.mock !== !!S.mock) return;

  const lesson = S.lessons.find(x => x.lesson_id === meta.lesson_id);
  if (!lesson) return;

  const rows = await draftItems(cur.sid);
  if (!rows.length) return;

  // 只有「还批得动的」才值得打扰老师：没批完、且图还在。已经批完的那些进历史，
  // 老师想看自己会去点，不该一开 App 就弹框。
  const pending = rows.filter(r => r.status !== "ok" && r.blob);
  if (!pending.length) return;

  // 没有图的 wait/run 是批不动的幽灵——摆进队列只会让老师反复去点。丢掉，
  // 但把数量说给他听：那是诚实且可行动的信息。
  const ghosts = rows.filter(r => !r.blob && r.status !== "ok" && r.status !== "err");
  const keep = rows.filter(r => ghosts.indexOf(r) < 0);
  if (ghosts.length) idbTx("items", "readwrite", (s) => { ghosts.forEach(r => s.delete(r.key)); });

  const yes = await askSheet(
    "上次批到一半",
    esc(meta.lesson_label || lesson.label) + " 还有 <b>" + pending.length + " 份</b>没批完。" +
    (ghosts.length ? "<br>其中 " + ghosts.length + " 份的照片没来得及存下，需要重拍。" : "") +
    "<br><span class=\"aside\">已经批好的那些不会丢，在「以前批过的」里随时能翻。</span>",
    "接着批", "先不批");
  if (!yes) return;   // ⚠ 不删——「先不批」只是这次不弹，不是要丢掉

  openSession(lesson, cur.sid, keep, true);
}

/* 把一课的记录装回队列视图。live=true 时会接着批没批完的那些。 */
function openSession(lesson, sid, rows, live) {
  S.lesson = lesson;
  S.sid = sid;
  dropItems();
  S.items = rows.map(r => ({
    id: r.id,
    file: null,                                        // 原图早就不在了，别假装还有
    blob: r.blob || null,
    url: r.blob ? URL.createObjectURL(r.blob) : "",    // url 必须重建，存下来的会是死链
    status: r.status === "run" ? "wait" : r.status,    // 上次正在飞的那份，回到待批
    result: r.result || null,
    error: r.error || "",
  }));
  // ⚠ 必须取最大 id，**不能用 length**——幽灵项被丢掉后 length 小于最大 id，
  //   新拍的照片就会拿到一个已经存在的 id。renderQueue 用 data-id 反查，撞了
  //   就会点开另一个学生的批语，然后老师把 A 的点评卡发给 B 的家长。
  S.seq = S.items.reduce((m, x) => Math.max(m, x.id), 0);

  renderBrief();
  renderQueue();
  go("grade", lesson.topic);
  if (live) pump();   // 放在最后：pump 花的是真钱，等老师真的进了这个视图再开始
}

/* ── 以前批过的 ─────────────────────────────── */
let histCount = 0;

async function refreshHist() {
  const ss = await draftSessions();
  histCount = ss.length;
  const el = $("#hist-entry");
  if (!el) return;
  el.hidden = !histCount;              // 一次都没批过时，整条不显示
  $("#hist-n").textContent = histCount;
}

async function renderHistory() {
  const ss = await draftSessions();
  const body = $("#hist-body");
  if (!ss.length) {
    body.innerHTML = `<p class="hint center">还没有批过的课。</p>`;
    return;
  }
  body.innerHTML = ss.map(m => {
    const d = new Date(m.updated || m.created || Date.now());
    const when = (d.getMonth() + 1) + "月" + d.getDate() + "日";
    const left = (m.total || 0) - (m.done || 0);
    return `<div class="hist-row">
      <button class="hist-open" data-sid="${esc(m.sid)}">
        <div class="t">${esc(m.lesson_label || "（这一课已经下架）")}</div>
        <div class="s">${when} · 批了 ${m.done || 0} 份${left > 0 ? "，还有 " + left + " 份没批完" : ""}</div>
        ${m.mock ? `<span class="tag unverified">演示模式批的</span>` : ""}
      </button>
      <button class="hist-del" data-sid="${esc(m.sid)}">删掉</button>
    </div>`;
  }).join("");

  $$("#hist-body .hist-open").forEach(b => { b.onclick = () => openHistSession(b.dataset.sid); });
  $$("#hist-body .hist-del").forEach(b => {
    b.onclick = async () => {
      const m = ss.find(x => x.sid === b.dataset.sid);
      const stay = await askSheet(
        "删掉这一课的批改？",
        esc((m && m.lesson_label) || "这一课") + " 批过的 <b>" + ((m && m.done) || 0) +
        " 份</b>批语会被删掉，删了找不回来。<br>" +
        "<span class=\"aside\">点评卡如果已经保存到相册，那些图不受影响。</span>",
        "先留着", "删掉");
      if (stay) return;
      await draftDropSession(b.dataset.sid);
      // 删的正好是当前这一课时，把队列也清干净，免得界面还留着已删的东西
      if (S.sid === b.dataset.sid) { dropItems(); S.sid = ""; }
      renderHistory();
      refreshHist();
    };
  });
}

async function openHistSession(sid) {
  const ss = await draftSessions();
  const m = ss.find(x => x.sid === sid);
  if (!m) return;

  // 演示模式批的东西，在真实模式下打开会出一张没有「非真实批改」水印、却带着
  // 品牌落款的点评卡——那能直接发进家长群。不给开。
  if (!!m.mock !== !!S.mock) {
    const stay = await askSheet(
      "这一课是演示模式批的",
      "当时服务器还没配密钥，批语是结构完整的**假数据**，没有参考价值；" +
      "现在打开还会生成不带「非真实批改」水印的点评卡。建议直接删掉。",
      "先留着", "删掉这一课");
    if (!stay) { await draftDropSession(sid); renderHistory(); refreshHist(); }
    return;
  }

  const lesson = S.lessons.find(l => l.lesson_id === m.lesson_id);
  if (!lesson) {
    await askSheet("这一课已经下架了",
      "标准包里找不到这一课了，批语还在但没法正常显示（档位和判据都读不到）。",
      "知道了", "删掉这一课").then(async (stay) => {
        if (!stay) { await draftDropSession(sid); renderHistory(); refreshHist(); }
      });
    return;
  }

  const rows = await draftItems(sid);
  if (!rows.length) return;
  openSession(lesson, sid, rows, false);   // live=false：图早清了，重批也批不了
}

/* ── 启动 ───────────────────────────────────── */
show("pick");
const lessonsP = loadLessons();
draftBoot(lessonsP);

// 全仓唯一一个 addEventListener。整个暂存功能就是为「被打断」服务的，而切后台
// 和锁屏正是最主要的那种打断——不 flush 就会丢掉老师改的最后几个字。
// 只加这一个：iOS 上 beforeunload 本就不可靠，不必再凑 pagehide 那一套。
$("#hist-entry").onclick = () => { renderHistory(); go("history", "以前批过的"); };

document.addEventListener("visibilitychange", () => { if (document.hidden) saveFlush(); });

$("#btn-clear-draft").onclick = async () => {
  // 以前这里只清 24 小时的暂存，不问也罢；现在它会把**所有批过的课**一起删掉，
  // 那是删数据，必须问一句。
  const stay = await askSheet(
    "清掉这台手机上的全部记录？",
    "包括<b>以前批过的 " + histCount + " 课</b>的批语，删了找不回来。<br>" +
    "<span class=\"aside\">只想删某一课的话，去「以前批过的」里单独删。" +
    "已经保存到相册的点评卡不受影响。</span>",
    "先留着", "全部删掉");
  if (stay) return;
  draftClearAll();
  dropItems();
  S.sid = "";
  renderQueue();
  refreshHist();
  const b = $("#btn-clear-draft");
  b.textContent = "已清掉";
  setTimeout(() => { b.textContent = "清掉这台手机上的暂存"; }, 1200);
  // 若此刻 pump 正在批：它持有 it 引用，会把当前这份跑完、把结果写回一个已被
  // 丢弃的对象，下一轮 find 返回 undefined 自然退出。无副作用，这是有意的。
};

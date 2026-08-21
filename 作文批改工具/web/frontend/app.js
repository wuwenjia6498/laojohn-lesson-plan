/* 老约翰 · 同步习作批改助手 · 前端
 *
 * 三条不要改掉的设计：
 * 1. 逐份**串行**批改，且把已生成的点评卡开头传给下一份（prev_heads）——
 *    一个班二三十份发同一个家长群，句式撞车这工具就废了。并发会让这道防线失效。
 * 2. 图片在本地压到长边 1600 再传：手机原图四五 MB，直传既慢又贵，
 *    而稿纸是黑字白纸、1600 足够认字。
 * 3. 前端不碰密钥、不存作文：图片对象只活在这一次会话的内存里，刷新即失。
 */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const S = {
  lessons: [],
  lesson: null,     // 当前课次（精简版标准包）
  items: [],        // 队列：{id, file, url, status, result, error}
  seq: 0,
  busy: false,
  mock: false,
};

const VCLS = { "达成": "v-ok", "部分达成": "v-half", "未达成": "v-no", "不适用": "v-na" };
const BCLS = ["b0", "b1", "b2"];

async function api(path, opts) {
  const r = await fetch(path, opts);
  let d = null;
  try { d = await r.json(); } catch (e) { /* 非 JSON 一律按下面的错处理 */ }
  if (!r.ok) throw new Error((d && d.error) || `请求失败（${r.status}）`);
  return d;
}

/* ── 视图路由 ───────────────────────────────── */
const VIEWS = ["pick", "grade", "detail", "class"];
let viewStack = ["pick"];

function show(name, title) {
  VIEWS.forEach(v => { $("#view-" + v).hidden = (v !== name); });
  $("#topbar-title").textContent = title || "同步习作批改助手";
  $("#btn-back").hidden = (name === "pick");
  $("#bottombar").hidden = !(name === "grade" && S.items.length);
  window.scrollTo(0, 0);
}

function go(name, title) {
  if (viewStack[viewStack.length - 1] !== name) viewStack.push(name);
  show(name, title);
}

$("#btn-back").onclick = () => {
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
// 最近用过：老师批一个班是同一课，连着几天多半还是它。存本地偏好，
// 不涉及任何学生数据（那条「不留存」的红线管的是作文原图与全文）。
const RECENT_KEY = "lj_recent_lessons";

function getRecent() {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]"); }
  catch (e) { return []; }
}

function pushRecent(id) {
  const r = [id, ...getRecent().filter(x => x !== id)].slice(0, 3);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(r)); } catch (e) { /* 隐私模式 */ }
}

async function loadLessons() {
  try {
    const h = await api("/api/health");
    S.mock = h.mock;
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

function pickLesson(l) {
  S.lesson = l;
  S.items = [];
  S.seq = 0;
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
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const w = Math.round(bmp.width * scale), h = Math.round(bmp.height * scale);
  const cv = document.createElement("canvas");
  cv.width = w; cv.height = h;
  cv.getContext("2d").drawImage(bmp, 0, 0, w, h);
  bmp.close && bmp.close();
  const blob = await new Promise(res => cv.toBlob(res, "image/jpeg", quality));
  return blob || file;
}

/* ── 队列 ───────────────────────────────────── */
$("#file-input").onchange = (e) => {
  const files = [...e.target.files];
  e.target.value = "";
  if (!files.length) return;
  files.forEach(f => S.items.push({
    id: ++S.seq, file: f, url: URL.createObjectURL(f),
    status: "wait", result: null, error: "",
  }));
  renderQueue();
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
      <img class="thumb" src="${it.url}" alt="">
      <div class="mid"><div class="name">${name}</div><div class="sub">${sub}</div></div>
      ${statusCell(it)}
      <span class="go">›</span>
    </button>`;
  }).join("");
  $$("#queue .card").forEach(b => {
    b.onclick = () => openDetail(S.items.find(x => x.id === +b.dataset.id));
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
      it.status = "run"; renderQueue();
      try {
        const fd = new FormData();
        fd.append("lesson_id", S.lesson.lesson_id);
        fd.append("prev_heads", JSON.stringify(
          S.items.filter(x => x.result && x.result.parent_card)
                 .map(x => x.result.parent_card.slice(0, 24))));
        fd.append("image", await shrink(it.file), "sheet.jpg");
        it.result = await api("/api/grade", { method: "POST", body: fd });
        it.status = "ok";
      } catch (e) {
        it.status = "err"; it.error = e.message;
      }
      renderQueue();
    }
  } finally { S.busy = false; }
}

/* ── 单份详情 ───────────────────────────────── */
let cur = null;

function openDetail(it) {
  cur = it;
  if (it.status === "err") {
    it.status = "wait"; it.error = "";
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
  ta.oninput = () => { cur.result.parent_card = ta.value; upd(); };
  upd();
  $("#in-name").oninput = (e) => { cur.result.student_name = e.target.value; };
  $("#ta-note").oninput = (e) => { cur.result.teacher_note = e.target.value; };
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

/* ── 启动 ───────────────────────────────────── */
show("pick");
loadLessons();

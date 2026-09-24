/* 课件配图工具 · 前端（原生 JS，无框架无构建）
 *
 * 三条约定：
 * 1. 服务端是唯一事实源。任何编辑都立即 PUT 回去，前端不留「未保存」状态——
 *    图要跑几分钟，中途关掉页面是常事，草稿留在内存里就没了。
 * 2. 分钟级操作一律拿 job id 轮询，界面显示逐条日志。生图慢是事实，
 *    藏起来只会让人以为卡死。
 * 3. 闸门文案要说清**为什么**拦你，不能只说「未通过」。
 */
const LF = '\n';   // 换行常量：源码里直接写反斜杠 n 容易在改文件时被吞
const $ = (s, r = document) => r.querySelector(s);
const el = (t, c, txt) => { const e = document.createElement(t);
  if (c) e.className = c; if (txt != null) e.textContent = txt; return e; };

async function api(path, opt = {}) {
  const r = await fetch('/api' + path, {
    ...opt,
    headers: opt.body instanceof FormData ? undefined
           : { 'Content-Type': 'application/json', ...(opt.headers || {}) },
  });
  const t = await r.text();
  let j; try { j = JSON.parse(t); } catch { j = { detail: t }; }
  if (!r.ok) throw new Error(j.detail || t);
  return j;
}

function openModal(title, node) {
  $('#modalTitle').textContent = title;
  $('#modalBody').innerHTML = ''; $('#modalBody').append(node);
  $('#modal').classList.remove('hidden');
}
function closeModal() { $('#modal').classList.add('hidden'); }

/* 轮询一个后台任务，实时告诉人「在做什么、等了多久」。
 *
 * 早先只画一条百分比进度条 + 一行日志：单张图 total=1，进度条只有 0% 和 100% 两态，
 * 中间 30–60 秒一动不动，看起来和卡死一模一样。现在必须给出三样：
 *   ① 正在做哪一张　② 已经等了几秒（每秒自己跳）　③ 通常要多久
 * 只有第 ② 项是「它还活着」的直接证据 —— 其余两样静态文字，卡死时长得一模一样。 */
function watchJob(jid, box, onDone) {
  const t0 = Date.now();
  const head = el('div', 'joghead');
  const bar = el('div', 'bar'); const fill = el('i'); bar.append(fill);
  const log = el('div', 'log');
  box.innerHTML = ''; box.append(head, bar, log);

  let finished = false, last = null;
  const paint = () => {
    if (finished) return;
    const secs = Math.round((Date.now() - t0) / 1000);
    const j = last;
    if (j && j.total > 1) {
      bar.classList.remove('indet');
      fill.style.width = (100 * j.done / j.total) + '%';
      head.textContent = '生成中　' + j.done + '/' + j.total + ' 张　已等 ' + secs + ' 秒'
        + '　（每张约 30–60 秒，共约 ' + Math.max(1, Math.round(j.total * 45 / 60)) + ' 分钟）';
    } else {
      bar.classList.add('indet');     // 单张：滚动条纹表示「在跑，但报不出进度」
      head.textContent = '生成中　已等 ' + secs + ' 秒　（通常 30–60 秒）';
    }
  };
  const timer = setInterval(paint, 1000);   // 秒数自己跳，不依赖轮询

  const tick = async () => {
    let j;
    try { j = await api('/jobs/' + jid); }
    catch (e) {
      clearInterval(timer); finished = true;
      head.textContent = '轮询失败'; log.textContent += LF + e.message; return;
    }
    last = j; paint();
    if (j.log.length) { log.textContent = j.log.join(LF); log.scrollTop = log.scrollHeight; }
    if (j.state === 'running') return setTimeout(tick, 1500);

    clearInterval(timer); finished = true;
    bar.classList.remove('indet'); fill.style.width = '100%';
    if (j.state === 'error') {
      fill.style.background = 'var(--warn)';
      // 报错第一行才是人要看的，traceback 折起来 —— 摊开一屏栈帧，
      // 真正那句「挂载的 X 还没生成」反而被埋在中间看不见。
      const raw = String(j.error || '');
      const first = raw.split(LF).find(x => x.trim()) || '未知错误';
      head.textContent = '✗ 失败（用时 ' + j.elapsed + 's）：'
        + first.replace(/^\w*(Error|Exit|Exception):\s*/, '').slice(0, 120);
      const det = el('details');
      det.append(el('summary', 'muted', '展开完整报错'));
      const pre = el('div', 'log'); pre.style.marginTop = '6px'; pre.textContent = raw;
      det.append(pre);
      log.replaceWith(det);
    } else {
      head.textContent = '✓ 完成，用时 ' + j.elapsed + ' 秒';
      if (j.result && j.result.机检) {
        log.textContent += j.result.机检.length
          ? LF + LF + '机检 ' + j.result.机检.length + ' 处：' + LF + '  ⚠ ' + j.result.机检.join(LF + '  ⚠ ')
          : LF + LF + '机检：低级错误一处没有';
        if (j.result.提示) log.textContent += LF + LF + j.result.提示;
      }
    }
    onDone && onDone(j);
  };
  paint(); tick();
}

/* ───────────────────── 项目列表 ───────────────────── */

// 新建项目表单的默认值。写成 value 而不是 placeholder 是有意的：
// placeholder 只是灰字提示，人还得从头敲一遍；默认值能直接改。
// 项目名重名不会静默覆盖——后端建项目时查重并报 409。
const DEFAULT_NAME = '三上-第一单元-猜猜他是谁';
const DEFAULT_STYLE = '水彩儿童插画：柔和水彩质感、干净留白';

async function viewHome() {
  const v = $('#view'); v.innerHTML = '';
  const head = el('div', 'card');
  head.append(el('h2', '', '新建项目'));
  head.insertAdjacentHTML('beforeend', `
    <p class="muted">两份都要传：<b>课件 pptx</b> 决定哪页要图、什么画幅（程序量出来的，是事实）；
    <b>教学详案</b> 决定画什么。少了 pptx 就只能让模型猜页码，实测会错位 1–3 页。</p>
    <div class="row" style="margin-bottom:10px">
      <label class="field" style="flex:1 1 240px"><span>项目名（也是产出目录名）</span>
        <input id="pName" value="${DEFAULT_NAME}" placeholder="三上-第一单元-猜猜他是谁"></label>
      <label class="field" style="flex:2 1 380px"><span>画风（改成你要的；清空则由模型推一个并标注待确认）</span>
        <input id="pStyle" value="${DEFAULT_STYLE}" placeholder="水彩儿童插画：柔和水彩质感、干净留白"></label>
      <label class="field" style="flex:0 1 200px"><span>手绘风格编号（选填，001–274）</span>
        <input id="pHanddraw" placeholder="如 105；填了就不用左边的画风"></label>
    </div>
    <div class="row" style="margin-bottom:10px">
      <label class="field" style="flex:1"><span>课件 .pptx</span><input type="file" id="pPptx" accept=".pptx"></label>
      <label class="field" style="flex:1"><span>教学详案 .md / .txt / .docx</span><input type="file" id="pPlan" accept=".md,.txt,.markdown,.docx"></label>
    </div>
    <div class="row"><button id="pGo">开始拆解</button>
      <span class="muted">拆解要调两次模型，约 1–2 分钟</span></div>
    <div id="pLog" style="margin-top:12px"></div>`);
  v.append(head);

  $('#pGo').onclick = async () => {
    const fd = new FormData();
    const name = $('#pName').value.trim();
    if (!name || !$('#pPptx').files[0] || !$('#pPlan').files[0])
      return alert('项目名、pptx、详案三样都要填。');
    fd.append('name', name); fd.append('style', $('#pStyle').value);
    fd.append('handdraw', $('#pHanddraw').value.trim());
    fd.append('pptx', $('#pPptx').files[0]); fd.append('plan', $('#pPlan').files[0]);
    $('#pGo').disabled = true;
    try {
      const { job } = await api('/projects', { method: 'POST', body: fd });
      watchJob(job, $('#pLog'), (j) => {
        $('#pGo').disabled = false;
        if (j.state === 'done') setTimeout(() => location.hash = '#/p/' + name, 1500);
      });
    } catch (e) { $('#pGo').disabled = false; alert(e.message); }
  };

  const list = el('div', 'card');
  list.append(el('h2', '', '项目'));
  const grid = el('div', 'grid projects');
  list.append(grid); v.append(list);

  const { projects } = await api('/projects');
  if (!projects.length) grid.append(el('p', 'muted', '还没有项目。'));
  for (const p of projects) {
    const c = el('div', 'card'); c.style.margin = '0'; c.style.cursor = 'pointer';
    if (p.错误) {
      c.append(el('h2', '', p.名称), el('p', 'muted', '读不出来：' + p.错误));
    } else {
      const charOK = p.闸门.char;
      c.innerHTML = `<h2>${p.名称}</h2>
        <p class="muted">角色件 ${p.角色已出}/${p.角色件}　页目 ${p.页目已出}/${p.页目}
        ${p.人工素材位 ? '　人工素材位 ' + p.人工素材位 : ''}</p>
        <div class="row">
          <span class="pill ${charOK ? 'ok' : ''}">定妆 ${charOK ? '已验 · ' + charOK : '未验收'}</span>
          <span class="pill ${p.闸门.pages ? 'ok' : ''}">页目 ${p.闸门.pages ? '已验 · ' + p.闸门.pages : '未验收'}</span>
          <span class="pill">${p.通道}</span>
        </div>`;
    }
    c.onclick = () => location.hash = '#/p/' + p.名称;

    // 删除按钮压在卡片右上角。必须 stopPropagation —— 整张卡片是「进项目」的点击区，
    // 不拦住冒泡就会变成「点了删除，然后跳进项目页」。
    const del = el('button', 'small ghost del', '删除');
    del.onclick = async (ev) => {
      ev.stopPropagation();
      const n = p.角色已出 + p.页目已出;
      const msg = '删掉项目「' + p.名称 + '」？' + LF + LF
        + (n ? '已生成的 ' + n + ' 张图会一起挪走。' + LF : '')
        + '不是真删：项目和图都会移进 _已删除/ 目录，想找回来可以搬回去。';
      if (!confirm(msg)) return;
      try {
        const r = await api('/projects/' + encodeURIComponent(p.名称), { method: 'DELETE' });
        await viewHome();
        alert('已移到：' + LF + r.已移到.join(LF));
      } catch (e) { alert(e.message); }
    };
    c.style.position = 'relative';
    c.append(del);
    grid.append(c);
  }
}

/* ───────────────────── 工作台 ───────────────────── */

let P = null, NAME = null;

const imgUrl = (sub, fn) => `/img/${encodeURIComponent(NAME)}/${sub}/${encodeURIComponent(fn)}.jpg?t=${Date.now()}`;

async function save(patch) {
  await api('/projects/' + encodeURIComponent(NAME),
            { method: 'PUT', body: JSON.stringify(patch) });
}

function thumb(sub, id, exists) {
  if (!exists) { const d = el('div', 'thumb miss', '未生成'); return d; }
  const i = el('img', 'thumb'); i.src = imgUrl(sub, id); i.loading = 'lazy';
  i.onclick = () => {
    const big = el('img'); big.src = imgUrl(sub, id);
    openModal(id, big);
  };
  return i;
}

async function viewProject(name) {
  NAME = name;
  P = await api('/projects/' + encodeURIComponent(name));
  const v = $('#view'); v.innerHTML = '';
  v.append(secHead(), secStyle(), secChars(), secSlides());
}

/* —— 顶栏：一行摘要 + 两个主操作 ——
 * 工作台的默认状态是「看图」，不是「改设置」。所以首屏只留进度和按钮，
 * 风格卡折起来、定妆缩成一排小图、清单用缩略图网格 —— 要改的东西点开才出现。 */
function secHead() {
  const c = el('div', 'card');
  const gen = P.slides.filter(s => s.通道 === '生成');
  const done = gen.filter(s => P.图状态.页目[s.页码]).length;
  const manual = P.slides.filter(s => s.通道 === '人工素材位').length;
  const h = el('h2', '', P.project?.名称 || NAME);
  const bar = el('div', 'row');
  const bAll = el('button', 'small', '生成未出的');
  bAll.onclick = () => {
    const todo = gen.filter(s => !P.图状态.页目[s.页码]).map(s => s.页码);
    if (!todo.length) return alert('每一页都有图了。要重出请点某一张的「重出」。');
    genImages('page', todo, false, c);
  };
  const bExp = el('button', 'small ghost', '导出');
  bExp.onclick = async () => {
    bExp.disabled = true; bExp.textContent = '打包中…';
    try {
      const r = await api(`/projects/${encodeURIComponent(NAME)}/export`, { method: 'POST' });
      // 直接把 zip 拉下来 —— 服务可能跑在别人的机器上，
      // 只把文件写到服务端目录，用的人一张也拿不到。
      if (r.下载) location.href = r.下载;
      setTimeout(() => alert(
        `✓ 导出 ${r.文件数} 张（${r.大小MB} MB），浏览器正在下载压缩包。

`
        + `服务端也留了一份：${r.目录}`), 400);
    } catch (e) { alert(e.message); }
    finally { bExp.disabled = false; bExp.textContent = '导出'; }
  };
  bar.append(bAll, bExp); h.append(bar); c.append(h);
  c.append(el('p', 'muted',
    `页目 ${done}/${gen.length}　角色件 ${P.characters.length}` +
    (manual ? `　人工素材位 ${manual}` : '') + `　${P.通道}`));
  return c;
}

/* —— 风格卡：默认折起，只露一行 —— */
function secStyle() {
  const s = P.style_card;
  const c = el('details', 'card');
  const sum = el('summary');
  sum.style.cssText = 'cursor:pointer;font-size:15px;font-weight:600';
  sum.append(document.createTextNode('风格卡'));
  sum.append(el('span', 'muted', '　' + (s.手绘编号 ? '手绘 #' + s.手绘编号 + '　' : '')
                               + (s.画风档 || '').slice(0, 46)));
  c.append(sum);
  const box = el('div'); box.style.paddingTop = '12px';
  box.append(el('p', 'muted',
    '手绘编号（001–274，与写作课海报同一套风格库）：填了之后，出图时画风改用该编号的特征并挂它的参考图，' +
    '「前缀基底」不再使用；清空则回到前缀基底。编号写错存不进去。'));
  for (const k of ['手绘编号', '画风档', '色板', '人物年龄设定', '场景基调', '概念母题',
                   '前缀基底', '人物条目', '文字禁令', '通用禁区']) {
    if (!(k in s) && k !== '手绘编号') continue;
    const lab = el('label', 'field'); lab.append(el('span', '', k));
    const t = el('textarea'); t.rows = 1;
    t.value = s[k] == null ? '' : (typeof s[k] === 'string' ? s[k] : JSON.stringify(s[k]));
    t.onchange = async () => {
      const old = s[k];
      if (k === '手绘编号' && !t.value.trim()) delete s[k]; else s[k] = t.value.trim();
      try { await save({ style_card: s }); }
      catch (e) { if (old === undefined) delete s[k]; else s[k] = old; t.value = old || ''; alert(e.message); }
    };
    lab.append(t); box.append(lab);
  }
  c.append(box);
  return c;
}

/* —— 角色件：一排小图，没有验收块（2026-08-29 用户要求去掉定妆检视） —— */
function secChars() {
  const c = el('div', 'card');
  if (!P.characters.length) {
    c.append(el('h2', '', '角色件'), el('p', 'muted', '本课每页人物都不同，不需要定妆图。'));
    return c;
  }
  const h = el('h2', '', '角色件');
  const b = el('button', 'small ghost', '全部重出');
  b.onclick = () => genImages('char', [], true, c);
  h.append(b); c.append(h);
  const row = el('div', 'row');
  for (const ch of P.characters) {
    const box = el('div'); box.style.cssText = 'text-align:center;width:110px';
    const t = thumb('角色', ch.id, P.图状态.角色[ch.id]);
    t.onclick = () => openChar(ch);
    box.append(t, el('div', 'muted', ch.id));
    row.append(box);
  }
  c.append(row);
  return c;
}

/* 点角色件 → 弹窗看大图并改描述 */
function openChar(ch) {
  const box = el('div');
  if (P.图状态.角色[ch.id]) {
    const im = el('img'); im.src = imgUrl('角色', ch.id); box.append(im);
  }
  const lab = el('label', 'field'); lab.append(el('span', '', `描述（${ch.画幅}）`));
  const t = el('textarea'); t.rows = 5; t.value = ch.prompt;
  t.onchange = async () => { ch.prompt = t.value; await save({ characters: P.characters }); };
  lab.append(t); box.append(lab);
  const row = el('div', 'row'); row.style.marginTop = '8px';
  const b = el('button', '', '按新描述重出');
  b.onclick = () => { closeModal(); genImages('char', [ch.id], true, $('#view')); };
  row.append(b);
  if (P.图状态.角色[ch.id]) {
    const dl = el('button', 'small ghost', '下载这张');
    dl.onclick = () => {
      location.href = `/dl/img/${encodeURIComponent(NAME)}/角色/`
                    + encodeURIComponent(ch.id + '.jpg');
    };
    row.append(dl);
  }
  box.append(row);
  openModal(ch.id, box);
}
/* —— 画面清单：缩略图网格。首屏就是一屏图，点某张才展开详情 ——
 * 原先是一张宽表：缩略图 + 用途 + 必现细节（带勾验框与来源）+ prompt 文本框 + 挂载 + 按钮，
 * 一行就占掉半屏，十几页看下来全是字。真正天天要做的事只有两件：看图、重出不满意的那张。
 * 所以网格只留「图 + 页码 + 用途」，改描述、勾必现细节都收进弹窗。 */
function secSlides() {
  const c = el('div', 'card');
  const h = el('h2', '', '画面清单');
  const bAdd = el('button', 'small ghost', '+ 新增画面');
  bAdd.onclick = () => openNewSlide();
  h.append(bAdd); c.append(h);
  const g = el('div', 'grid slides');
  for (const s of P.slides) {
    const pg = s.页码;
    const box = el('div', 'slide'); box.dataset.pg = pg;
    const manual = s.通道 === '人工素材位';
    const reused = s.通道 === '复用' ? s.复用 : null;
    const has = manual ? false : (P.图状态.页目[pg] || (reused && P.图状态.页目[reused]));
    let t;
    // 复用页一律按**源页码**取图。别用它自己的页码 —— 磁盘上可能留着上一轮的同名残留，
    // 取到的会是上一版画风的旧图，而界面上完全看不出来。
    if (manual) t = el('div', 'thumb miss', '人工素材');
    else if (reused) t = thumb('页目', reused, P.图状态.页目[reused]);
    else t = thumb('页目', pg, P.图状态.页目[pg]);
    t.style.width = '100%'; t.style.height = '150px';
    t.onclick = () => openSlide(s);
    box.append(t);
    // 图比描述旧 —— 必须在缩略图上就看得见。否则人对着一张不相干的图
    // 反复读描述找原因（实测：封面描述已改成「主角色剪影」，显示的还是早先那张帆布包）。
    if ((P.图状态.过期 || []).includes(pg)) box.classList.add('stale');
    const cap = el('div', 'cap');
    cap.append(el('b', '', pg));
    if (s.类型) cap.append(el('span', 'tag', s.类型));
    if (reused) cap.append(el('span', 'tag', '复用 ' + reused));
    box.append(cap, el('div', 'muted', s.用途 || ''));
    g.append(box);
  }
  c.append(g);
  c.append(el('p', 'muted',
    '点任意一张：看大图、改描述、勾必现细节、重出。比喻拆没拆、画面对不对，程序判不了，得看图。'));
  return c;
}

/* 新增一个清单之外的画面。
 * 拆解器给的是候选不是定论 —— 实测页级命中 11/16，漏的那几页得能补回来；
 * 想给某页多配一张、或加一张备用图，也走这里。 */
function openNewSlide() {
  const box = el('div');
  const mk = (label, hint) => {
    const l = el('label', 'field');
    l.append(el('span', '', label + (hint ? '　' + hint : '')));
    return l;
  };
  const lPg = mk('页码', '可写 P08、P08-2，也可写「备用-封面」；会用作文件名');
  const iPg = el('input'); iPg.placeholder = 'P08-2'; lPg.append(iPg);
  const lUse = mk('用途', '一句话说清这张图在这页干什么');
  const iUse = el('input'); iUse.placeholder = '例子类配图：展示「摘草莓」这件事'; lUse.append(iUse);

  const row = el('div', 'row');
  const lTy = mk('类型'); const sTy = el('select');
  ['例子', '场景', '道具', '素材'].forEach(v => { const o = el('option', '', v); o.value = v; sTy.append(o); });
  lTy.append(sTy); lTy.style.flex = '1';
  const lRt = mk('画幅'); const sRt = el('select');
  ['1:1', '3:4', '4:3', '16:9'].forEach(v => { const o = el('option', '', v); o.value = v; sRt.append(o); });
  lRt.append(sRt); lRt.style.flex = '1';
  row.append(lTy, lRt);

  const lPr = mk('描述', '发送时会自动拼上风格前缀');
  const tPr = el('textarea'); tPr.rows = 5;
  tPr.placeholder = '挂载参考图里的那个小男孩双手捧着几颗草莓，近景构图，主体占据画面主要面积…';
  lPr.append(tPr);

  // 「按用途起草」：手写描述要同时照顾一堆规则 —— 挂载得在正文点名、数量只写一遍、
  // 有纸就得禁文字、还不能和已有页撞同一件道具 —— 人记不住这么多。
  // 让模型起草、人来改，比从零写省事，也更容易合规。
  const draftRow = el('div', 'row');
  const bDraft = el('button', 'small ghost', '按用途起草描述');
  const dHint = el('span', 'muted', '会读这一课的画风、角色件和已有图位，避免撞车');
  draftRow.append(bDraft, dHint);
  bDraft.onclick = async () => {
    const u = iUse.value.trim();
    if (!u) return alert('先填「用途」——这张图要干什么，一句话就行。');
    bDraft.disabled = true; bDraft.textContent = '起草中…';
    try {
      const r = await api(`/projects/${encodeURIComponent(NAME)}/draft-slide`,
                          { method: 'POST', body: JSON.stringify({ 用途: u }) });
      tPr.value = r.prompt || '';
      if (r.类型) sTy.value = r.类型;
      if (r.画幅) sRt.value = r.画幅;
      mounts.forEach(cb => { cb.checked = (r.挂载 || []).includes(cb.value); });
      drafted = r;                       // 必现细节随表单一起提交
      dHint.textContent = r._说明 ? '起草说明：' + r._说明 : '起草好了，按需改。';
    } catch (e) { alert(e.message); }
    finally { bDraft.disabled = false; bDraft.textContent = '重新起草'; }
  };

  box.append(lPg, lUse, row, draftRow, lPr);

  let drafted = null;
  const mounts = [];
  if (P.characters.length) {
    const lM = mk('挂载参考图', '挂了就要在描述里提一句「挂载参考图里的…」，否则等于没挂');
    const mrow = el('div', 'row');
    for (const ch of P.characters) {
      const lab = el('label'); lab.style.cssText = 'display:flex;gap:5px;align-items:center;width:auto';
      const cb = el('input'); cb.type = 'checkbox'; cb.value = ch.id; cb.style.width = 'auto';
      lab.append(cb, document.createTextNode(ch.id));
      mrow.append(lab); mounts.push(cb);
    }
    lM.append(mrow); box.append(lM);
  }

  const b = el('button', '', '加进清单');
  b.onclick = async () => {
    const body = {
      页码: iPg.value.trim(), 用途: iUse.value.trim(), 类型: sTy.value,
      画幅: sRt.value, prompt: tPr.value.trim(),
      挂载: mounts.filter(x => x.checked).map(x => x.value),
      // 起草出来的必现细节一并存下 —— 机检读的正是这几条，
      // 丢了它这一页就查不出人数写两遍、漏挂定妆、纸面没禁字这些毛病。
      必现细节: (drafted && drafted.必现细节) || [],
      来源: (drafted && drafted.来源) || [],
    };
    if (!body.页码) return alert('页码要填。');
    if (!body.prompt) return alert('描述要填，否则生成时只剩风格前缀，会画出一张不相干的图。');
    try {
      await api(`/projects/${encodeURIComponent(NAME)}/slides`,
                { method: 'POST', body: JSON.stringify(body) });
      closeModal(); await viewProject(NAME);
    } catch (e) { alert(e.message); }
  };
  box.append(b);
  box.append(el('p', 'muted', '加进清单后不会自动生成，回到清单点那张卡片再生成。'));
  openModal('新增画面', box);
}

/* 点某一页 → 弹窗：左大图，右必现细节与描述 */
function openSlide(s) {
  const pg = s.页码;
  const wrap = el('div');
  wrap.style.cssText = 'display:grid;grid-template-columns:minmax(260px,1fr) 1fr;gap:18px;align-items:start';
  const left = el('div');
  const reused = s.通道 === '复用' ? s.复用 : null;
  const shown = reused ? (P.图状态.页目[reused] ? reused : null)
                       : (P.图状态.页目[pg] ? pg : null);
  if (shown) { const im = el('img'); im.src = imgUrl('页目', shown); left.append(im); }
  else left.append(el('div', 'thumb miss', s.通道 === '人工素材位' ? '人工素材位' : '未生成'));
  if (s._说明) left.append(el('p', 'muted', s._说明));
  if (shown) {
    const dl = el('button', 'small ghost', '下载这张');
    dl.style.marginTop = '8px';
    dl.onclick = () => {
      location.href = `/dl/img/${encodeURIComponent(NAME)}/页目/`
                    + encodeURIComponent(shown + '.jpg');
    };
    left.append(dl);
  }
  wrap.append(left);

  const right = el('div');
  if ((P.图状态.过期 || []).includes(pg)) {
    const w = el('p', 'stalewarn');
    w.textContent = '⚠ 左边这张图是按旧描述画的。项目重新拆解过，描述已经变了 ——'
                  + '图不会跟着变，要点下面的「按当前描述重出」才对得上。';
    right.append(w);
  }
  right.append(el('p', '', s.用途 || ''));
  if ((s.必现细节 || []).length) {
    // 这里原来每条前面有个 checkbox。查证后确认它没有任何作用 ——
    // 勾选状态存进 `_勾验` 并落盘，但后端不读、机检不看、导出不体现、也不阻断什么；
    // 闸门改成不阻断之后，它连「验收前置」这个身份也没了。
    // 加上逐条勾的成本很高（一课 20 多张 × 每张四条），实际不会有人去点，
    // 于是删掉方框、只留内容。**必现细节本身要留**：看图时逐条核对靠它，
    // 机检判人数、漏挂定妆、道具撞车、纸面禁文字也全读这几条。
    right.append(el('div', 'muted', '必现细节（对着图逐条核对；机检也读这几条）'));
    const ul = el('ul', 'checks');
    (s.必现细节 || []).forEach((d, i) => {
      const li = el('li');
      li.append(el('span', 'dot', '·'), el('span', '', d));
      const src = (s.来源 || [])[i];
      if (src) li.append(el('span', 'src', src));
      ul.append(li);
    });
    right.append(ul);
  }
  if (s.通道 !== '人工素材位' && !reused) {
    // 一个输入框 + 一个模式开关，而不是并排摆两个框。
    // 两个 textarea 长得一样，填错框的后果却不对称：把「男孩站到讲台前」这种
    // 增量指令填进「完整描述」再重出，模型只看得到这一句，会画出一张不相干的图，
    // 而原图已被覆盖。开关放在框上面，切换时框的内容和按钮文字一起变，填错不了。
    const hasImg = !!P.图状态.页目[pg];
    const wrapEd = el('div');
    const modes = el('div', 'modes');
    const mkRadio = (val, text, hint) => {
      const l = el('label', 'mode');
      const r = el('input'); r.type = 'radio'; r.name = 'genmode'; r.value = val;
      r.checked = (val === 'full');
      l.append(r, el('b', '', text), el('span', 'muted', hint));
      return l;
    };
    modes.append(mkRadio('full', '重新画一张', '照下面这整段描述从零画，原图被覆盖'));
    if (hasImg) modes.append(mkRadio('edit', '在这张图上改', '只写要改的那一句，其余保持不动'));
    wrapEd.append(modes);

    const lab = el('label', 'field');
    const cap = el('span', '', '完整描述（发送时会自动拼上风格前缀）');
    // 「恢复初稿」**始终显示**，改没改过用禁用态表示。
    // 上一版做成「改过才出现」，结果给存量项目补初稿时用的是当前值，
    // 两者永远相等、按钮永不出现 —— 一个看不见的功能等于没有。
    // 看得见但灰着，至少告诉人「有这么个东西，现在用不上」。
    const rev = el('button', 'small ghost', '恢复初稿');
    rev.type = 'button';
    rev.style.cssText = 'float:right;margin-top:-2px';
    lab.append(cap, rev);
    const ta = el('textarea'); ta.rows = 6; ta.value = s.prompt || '';
    lab.append(ta); wrapEd.append(lab);
    // 挂载改成可勾：除了角色件，还能挂**别页已生成的图**。
    // 对比图、同场景变体全靠它 —— 在描述里写「和上一张同样构图」是没用的，
    // 模型看不到上一张，那句话等于没说。
    const mlab = el('label', 'field');
    mlab.append(el('span', '', '挂载参考图（勾了要在描述里点名「挂载参考图里的…」，否则等于没挂）'));
    const mbox = el('div', 'mounts');
    const cur = new Set(s.挂载 || []);
    const addGrp = (title, list) => {
      if (!list.length) return;
      mbox.append(el('div', 'muted', title));
      const row = el('div', 'row');
      for (const id of list) {
        const lb = el('label'); lb.style.cssText = 'display:flex;gap:5px;align-items:center;width:auto';
        const cb = el('input'); cb.type = 'checkbox'; cb.value = id;
        cb.checked = cur.has(id); cb.style.width = 'auto';
        cb.onchange = async () => {
          const set = new Set(s.挂载 || []);
          cb.checked ? set.add(id) : set.delete(id);
          s.挂载 = [...set];
          await save({ slides: P.slides });
        };
        lb.append(cb, document.createTextNode(id));
        row.append(lb);
      }
      mbox.append(row);
    };
    addGrp('角色件', P.characters.map(c => c.id));
    addGrp('别页的图（挂上去当构图参考）',
           P.slides.filter(x => x.页码 !== pg && x.通道 === '生成' && P.图状态.页目[x.页码])
                   .map(x => x.页码));
    mlab.append(mbox); wrapEd.append(mlab);

    const btn = el('button', '', hasImg ? '按当前描述重出' : '生成');
    const tip = el('p', 'muted', '');
    wrapEd.append(btn, tip);

    let mode = 'full';
    const draft = s._初稿prompt || '';
    const syncRev = () => {
      if (mode !== 'full' || !draft) { rev.style.display = 'none'; return; }
      rev.style.display = '';
      const changed = ta.value.trim() !== draft.trim();
      rev.disabled = !changed;
      rev.textContent = changed ? '恢复初稿' : '未改动';
      rev.title = changed ? '换回拆解器最初写的那版' : '当前描述就是初稿，没有可恢复的';
    };
    const saveFull = async () => { s.prompt = ta.value; await save({ slides: P.slides }); syncRev(); };
    ta.onchange = () => { if (mode === 'full') saveFull(); };
    ta.oninput = syncRev;
    rev.onclick = async () => {
      if (!confirm('把描述换回拆解器最初写的那版？当前这版会丢掉。')) return;
      ta.value = draft; await saveFull();
    };
    syncRev();

    wrapEd.querySelectorAll('input[name=genmode]').forEach(r => {
      r.onchange = () => {
        mode = r.value;
        if (mode === 'full') {
          cap.textContent = '完整描述（发送时会自动拼上风格前缀）';
          ta.value = s.prompt || ''; ta.placeholder = '';
          ta.rows = 6; btn.textContent = '按当前描述重出';
          tip.textContent = ''; syncRev();
        } else {
          cap.textContent = '要改哪里（只写这一句，不要重写整段）';
          ta.value = ''; ta.placeholder = '例：男孩站到讲台前，面对着台下的同学';
          ta.rows = 2; btn.textContent = '在这张图上改'; syncRev();
          tip.innerHTML = '<b>改得动</b>：换个颜色、换个姿势或位置、把画面里某样东西去掉。<br>'
            + '<b>不太行</b>：往画面里添人、或者说「随便去掉一个」——这两种建议改用「重新画一张」。<br>'
            + '每次改动前会自动存一份原图，下面「改过的版本」里能点回去。';
        }
      };
    });

    btn.onclick = () => {
      const t = ta.value.trim();
      if (!t) return alert(mode === 'full' ? '描述是空的，填上再重出。' : '写一句要改哪里。');
      if (mode === 'full') saveFull();
      closeModal();
      genImages(mode === 'full' ? 'page' : 'edit', [pg], true, $('#view'),
                mode === 'edit' ? t : undefined);
    };
    right.append(wrapEd);
  }

  // 手工新增的条目给个删除口；拆解器产出的不给 —— 删了机检就对不上账
  // （它按 deck 的页数核对每页有没有结论），而且重新拆解会把它带回来。
  if (s._手工新增) {
    const db = el('button', 'small ghost', '删掉这条');
    db.style.cssText = 'margin-top:10px;color:var(--warn);border-color:var(--warn)';
    db.onclick = async () => {
      if (!confirm(`把「${pg}」从清单里删掉？（已生成的图仍留在盘上）`)) return;
      try {
        await api(`/projects/${encodeURIComponent(NAME)}/slides/${encodeURIComponent(pg)}`,
                  { method: 'DELETE' });
        closeModal(); await viewProject(NAME);
      } catch (e) { alert(e.message); }
    };
    right.append(db);
  }

  // 历史版本：存在磁盘上人是看不见的，得能列出来、点得回去，
  // 否则「改坏了可以还原」只是一句空话。
  if (s.通道 === '生成') {
    const hbox = el('div');
    hbox.style.cssText = 'margin-top:16px;padding-top:12px;border-top:1px solid var(--line)';
    right.append(hbox);
    loadHistory(pg, hbox);
  }

  wrap.append(right);
  openModal(pg + (s.类型 ? '　' + s.类型 : ''), wrap);
}

async function genImages(kind, ids, force, card, instruction) {
  // 日志固定挂在一个容器里复用，不要每次 append 一个新的 ——
  // 实测点两次「重出」就在页面末尾摞出两个黑框，且都停在第一行不动，
  // 看起来像卡死，其实是前一个框的轮询已经结束、没人再更新它。
  let box = $('#genlog');
  if (!box) {
    box = el('div'); box.id = 'genlog'; box.style.marginTop = '12px';
    (card || $('#view')).append(box);
  }
  box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  // 直接在那几张卡片上盖一层「生成中」——不然人得滚到页面底下的黑条里去找，
  // 而黑条只说「开始了」，说不清是哪张、还要多久。
  const marked = [];
  if (kind === 'page' || kind === 'edit') {
    for (const pg of (ids.length ? ids : [])) {
      const cardEl = document.querySelector(`.slide[data-pg="${CSS.escape(pg)}"]`);
      if (cardEl) { cardEl.classList.add('busy'); marked.push(cardEl); }
    }
  }
  const unmark = () => marked.forEach(e => e.classList.remove('busy'));
  try {
    const { job } = await api(`/projects/${encodeURIComponent(NAME)}/gen`,
      { method: 'POST', body: JSON.stringify({ kind, ids, force, instruction }) });
    watchJob(job, box, (j) => {
      unmark();
      if (j.state === 'done') setTimeout(() => viewProject(NAME), 900);
    });
  } catch (e) { unmark(); box.innerHTML = ''; box.append(el('div', 'log', e.message)); }
}

async function loadHistory(pg, box) {
  let r;
  try { r = await api(`/projects/${encodeURIComponent(NAME)}/history/${encodeURIComponent(pg)}`); }
  catch { return; }
  if (!r.版本.length) return;
  box.append(el('div', 'muted', `改过的版本（${r.版本.length} 个，新的在前）`));
  const row = el('div', 'hist');
  for (const v of r.版本) {
    const cell = el('div', 'histcell');
    const im = el('img');
    im.src = `/hist/${encodeURIComponent(NAME)}/${encodeURIComponent(v.文件)}`;
    im.onclick = () => { const big = el('img'); big.src = im.src; openModal(v.时间, big); };
    cell.append(im, el('div', 'muted', v.时间));
    const b = el('button', 'small ghost', '还原这张');
    b.onclick = async () => {
      if (!confirm(`用 ${v.时间} 这一版覆盖当前图？
（当前图会先存进历史，可以再换回来）`)) return;
      try {
        await api(`/projects/${encodeURIComponent(NAME)}/restore`,
          { method: 'POST', body: JSON.stringify({ 页码: pg, 文件: v.文件 }) });
        closeModal(); await viewProject(NAME);
      } catch (e) { alert(e.message); }
    };
    cell.append(b);
    row.append(cell);
  }
  box.append(row);
}

/* ───────────────────── 路由与启动 ───────────────────── */

async function route() {
  const h = location.hash;
  try {
    if (h.startsWith('#/p/')) await viewProject(decodeURIComponent(h.slice(4)));
    else await viewHome();
  } catch (e) {
    $('#view').innerHTML = `<div class="card"><h2>出错了</h2><div class="log">${e.message}</div></div>`;
  }
}

$('#btnHome').onclick = () => { location.hash = ''; };
$('#btnRules').onclick = async () => {
  const { text } = await api('/rules');
  const pre = el('div', 'log'); pre.style.maxHeight = '70vh'; pre.textContent = text;
  openModal('拆解规则库（只读）', pre);
};
$('#modal').onclick = (e) => { if (e.target.id === 'modal') closeModal(); };
window.addEventListener('hashchange', route);

(async () => {
  try {
    const h = await api('/health');
    const p = $('#health');
    if (h.密钥) { p.className = 'pill ok'; p.textContent = `${h.通道} · ${h.生图模型}`; }
    else { p.className = 'pill bad'; p.textContent = '缺密钥：' + (h.错误 || '').slice(0, 40); }
  } catch { $('#health').textContent = '服务未就绪'; }
  route();
})();

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const paths = {
  search:'<circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  settings:'<path d="m10 3-.6 2.1-2 .9-2-.6-2 3.5 1.5 1.5v2.3L3.4 14l2 3.5 2-.6 2 .9L10 20h4l.6-2.2 2-.9 2 .6 2-3.5-1.5-1.3v-2.3l1.5-1.5-2-3.5-2 .6-2-.9L14 3Z"/><circle cx="12" cy="11.5" r="3"/>',
  moon:'<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  'arrow-up-right':'<path d="M6 18 18 6M6 6h12v12"/>',
  'arrow-right':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  'arrow-up':'<path d="M12 20V4m-6 6 6-6 6 6"/>',
  'chevron-left':'<path d="m15 5-7 7 7 7"/>',
  'chevron-right':'<path d="m9 5 7 7-7 7"/>',
  'chevron-down':'<path d="m6 9 6 6 6-6"/>',
  book:'<path d="M3 4h6a4 4 0 0 1 3 2 4 4 0 0 1 3-2h6v15h-6a4 4 0 0 0-3 2 4 4 0 0 0-3-2H3Zm9 2v15"/>',
  leaf:'<path d="M20 3c0 9-2 15-9 15a6 6 0 0 1 0-12c4 0 7-1 9-3ZM4 21l11-11"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  external:'<path d="M14 3h7v7m0-7L10 14M10 4H4v16h16v-6"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  upload:'<path d="M12 16V4m-5 5 5-5 5 5M4 16v5h16v-5"/>',
  sparkles:'<path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6ZM21 2v4m-2-2h4"/>',
  bookmark:'<path d="M6 3h12v18l-6-4-6 4Z"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  layers:'<path d="m12 3 10 5-10 5L2 8Zm-10 9 10 5 10-5M2 16l10 5 10-5"/>',
  'align-left':'<path d="M4 5h16M4 10h12M4 15h16M4 20h9"/>',
  pen:'<path d="m15 4 5 5M4 20l5-1L21 7l-5-5L4 14Z"/>',
  'message-plus':'<path d="M20 12v5H9l-5 4V4h12m4-3v8m-4-4h8"/>',
  link:'<path d="m9 15 6-6m-8 9-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m2 8a4 4 0 0 0 6 0l5-5a4 4 0 0 0-6-6l-1 1" transform="translate(1 0) scale(.9)"/>',
  shield:'<path d="m12 2 8 3v6c0 5-4 9-8 11-4-2-8-6-8-11V5Zm-4 9 3 3 5-6"/>',
  close:'<path d="m5 5 14 14M5 19 19 5"/>',
  refresh:'<path d="M20 8a8 8 0 1 0 .5 7M20 3v6h-6"/>',
  file:'<path d="M14 2H5v20h14V7Zm0 0v6h5M8 13h8m-8 4h6"/>',
  code:'<path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18"/>',
  warning:'<path d="M12 3 2 21h20Zm0 6v5m0 3h.01"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.file}</svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function icons(root = document) { $$('[data-icon]', root).forEach(el => { el.innerHTML = icon(el.dataset.icon); }); }
function time(value) { const n = Math.max(0, Math.floor(Number(value) || 0)); return n >= 3600 ? `${Math.floor(n/3600)}:${String(Math.floor(n/60)%60).padStart(2,'0')}:${String(n%60).padStart(2,'0')}` : `${String(Math.floor(n/60)).padStart(2,'0')}:${String(n%60).padStart(2,'0')}`; }
function duration(value) { const n = Number(value) || 0; return n >= 60 ? `${Math.round(n / 60)} 分钟` : `${Math.round(n)} 秒`; }
function bytes(n) { n = Number(n) || 0; return n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(1)} MB`; }
function safeUrl(value) { try { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) ? u.href : ''; } catch { return ''; } }
function imageUrl(value) { if (!value) return ''; if (/^\/demo-slides\/[a-zA-Z0-9_-]+\.svg$/.test(value)) return value; const u = safeUrl(value); return u ? `/api/assets?url=${encodeURIComponent(u)}` : ''; }

// A deliberately small renderer: all source text is escaped before markup is added.
function inline(text) {
  let s = esc(text);
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_, label, url) => {
    const clean = safeUrl(url.replace(/&amp;/g, '&'));
    return clean ? `<a href="${esc(clean)}" target="_blank" rel="noopener noreferrer">${label}</a>` : label;
  });
  return s;
}
function markdown(value) {
  const lines = String(value || '').replace(/\r/g, '').split('\n');
  let html = '', code = null, list = null;
  const closeList = () => { if (list) html += `</${list}>`; list = null; };
  for (const line of lines) {
    if (/^\s*```/.test(line)) { closeList(); if (code !== null) { html += `<pre><code>${esc(code.join('\n'))}</code></pre>`; code = null; } else code = []; continue; }
    if (code !== null) { code.push(line); continue; }
    const heading = line.match(/^\s*(#{1,6})\s+(.+)$/);
    const bullet = line.match(/^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+)$/);
    if (heading) { closeList(); const h = Math.min(4, heading[1].length + 1); html += `<h${h}>${inline(heading[2])}</h${h}>`; }
    else if (bullet) { const type = /^\s*\d/.test(line) ? 'ol' : 'ul'; if (list !== type) { closeList(); list = type; html += `<${type}>`; } html += `<li>${inline(bullet[1])}</li>`; }
    else if (/^\s*>/.test(line)) { closeList(); html += `<blockquote>${inline(line.replace(/^\s*>\s?/, ''))}</blockquote>`; }
    else if (/^\s*---+\s*$/.test(line)) { closeList(); html += '<hr>'; }
    else if (line.trim()) { closeList(); html += `<p>${inline(line)}</p>`; }
    else closeList();
  }
  closeList(); if (code !== null) html += `<pre><code>${esc(code.join('\n'))}</code></pre>`;
  return html;
}
async function api(path, options = {}) {
  const opt = {...options, headers:{'Content-Type':'application/json', ...(options.headers || {})}};
  if (opt.body && typeof opt.body !== 'string') opt.body = JSON.stringify(opt.body);
  const response = await fetch(path, opt);
  let result; try { result = await response.json(); } catch { throw new Error(`服务器返回了无法读取的响应（${response.status}）`); }
  if (!response.ok) throw new Error(typeof result.error === 'string' ? result.error : result.message || result.detail || `请求失败（${response.status}）`);
  return result;
}
function toast(message, type='success') {
  const el = document.createElement('div'); el.className=`toast ${type}`;
  el.innerHTML=`<span data-icon="${type==='error'?'warning':'check'}"></span><span>${esc(message)}</span>`; icons(el); $('#toast-stack').append(el);
  setTimeout(() => el.remove(), type==='error'?9000:4200);
}
let remembered = {}; try { remembered = JSON.parse(localStorage.getItem('synapse-view') || '{}'); } catch {}
const S = {courses:[],lectures:[],stats:{},settings:{},courseId:remembered.courseId||null,lecture:null,slideIndex:0,tab:'knowledge',filter:'all',scope:'slide',messages:[],chatBusy:false,chatController:null,chatSequence:0,lectureSequence:0,drafts:new Map(),savedNotes:new Map(),jobs:new Map(),searchSequence:0,importTab:'canvas'};
function remember() { try { localStorage.setItem('synapse-view', JSON.stringify({courseId:S.courseId,lectureId:S.lecture?.id,slideId:currentSlide()?.id})); } catch {} }
function currentSlide() { return S.lecture?.slides?.[S.slideIndex]; }
function contextKey() { return [S.lecture?.id||'',S.scope,S.scope==='slide'?currentSlide()?.id||'':''].join(':'); }
function contextQuery() { return new URLSearchParams({lecture_id:S.lecture?.id||'',scope:S.scope,slide_id:S.scope==='slide'?currentSlide()?.id||'':''}).toString(); }
function showModal(content) { $('#modal-content').innerHTML=content; icons($('#modal')); if (!$('#modal').open) $('#modal').showModal(); }
function modalHeader(title,desc='') { return `<div class="modal-header"><div><h2>${esc(title)}</h2>${desc?`<p>${esc(desc)}</p>`:''}</div><button class="icon-button" data-action="close-modal" aria-label="关闭">${icon('close')}</button></div>`; }
function closeModal() { $('#modal').close(); }
function inlineError(message, selector='#modal-error') { const el=$(selector); if (el) { el.hidden=!message; el.textContent=message||''; } else if (message) toast(message,'error'); }

async function loadState(selectRemembered=false) {
  const data=await api('/api/state'); S.courses=data.courses||[];S.lectures=data.lectures||[];S.stats=data.stats||{};S.settings=data.settings||S.settings;
  if (!S.courses.some(c=>String(c.id)===String(S.courseId))) S.courseId=S.courses[0]?.id||null;
  renderLibrary(); renderModelStatus();
  if (selectRemembered) {
    const candidates=S.lectures.filter(l=>String(l.course_id)===String(S.courseId));
    const id=candidates.find(l=>String(l.id)===String(remembered.lectureId))?.id||candidates[0]?.id;
    if (id) await loadLecture(id,remembered.slideId);
    else renderEmpty();
  }
}
function renderLibrary() {
  $('#course-count').textContent=S.courses.length;
  $('#course-list').innerHTML=S.courses.map(c=>`<button class="course-card ${String(c.id)===String(S.courseId)?'selected':''}" data-course="${esc(c.id)}" aria-pressed="${String(c.id)===String(S.courseId)}"><span class="course-icon">${icon('book')}</span><div class="course-copy"><strong title="${esc(c.title)}">${esc(c.title)}</strong><span>${esc([c.teacher,c.term].filter(Boolean).join(' · ')||'本地课程')}</span></div></button>`).join('');
  const lectures=S.lectures.filter(l=>String(l.course_id)===String(S.courseId)); $('#lecture-count').textContent=`${lectures.length} 节`;
  $('#lecture-list').innerHTML=lectures.length?lectures.map((l,i)=>`<button class="lecture-item ${String(l.id)===String(S.lecture?.id)?'selected':''}" data-lecture="${esc(l.id)}"><strong title="${esc(l.title)}">${esc(l.title)}</strong><small>${esc((l.date||'').slice(0,10))}${l.duration?` · ${duration(l.duration)}`:''}</small>${l.slide_count?`<div class="review-track" aria-label="学习进度"><i style="width:${Math.min(100,100*(l.reviewed_count||0)/l.slide_count)}%"></i></div>`:''}</button>`).join(''):'<div class="sidebar-empty">还没有导入课堂。<br>点击上方「导入课堂」开始。</div>';
}
function renderEmpty() { $('#empty-workspace').hidden=false;$('#lecture-workspace').hidden=true;S.lecture=null;updateContext();renderChatWelcome(); }
async function loadLecture(id, slideId=null) {
  const seq=++S.lectureSequence;
  try {
    const lecture=await api(`/api/lectures/${encodeURIComponent(id)}`);
    if (seq!==S.lectureSequence) return;
    cancelChat();S.lecture=lecture;S.courseId=lecture.course_id;S.slideIndex=Math.max(0,(lecture.slides||[]).findIndex(s=>String(s.id)===String(slideId)));S.filter='all';
    for (const slide of lecture.slides||[]) if (!S.drafts.has(slide.id)) S.savedNotes.set(slide.id,slide.notes||'');
    $('#empty-workspace').hidden=true;$('#lecture-workspace').hidden=false;renderLibrary();renderLecture();remember();await loadHistory();
  } catch(e) { if(seq===S.lectureSequence)toast(e.message,'error'); }
}
function renderLecture() {
  const l=S.lecture;if(!l)return;
  $('#lecture-breadcrumb').innerHTML=`${icon('book')}<span>${esc(l.course_title||S.courses.find(c=>String(c.id)===String(l.course_id))?.title||'课程')}</span>${icon('chevron-right')}<span>课堂回放</span>`;
  $('#lecture-title').textContent=l.title||'未命名课堂';
  $('#lecture-meta').innerHTML=`<span>${esc(l.date||'未提供日期')}</span><span>${l.duration?duration(l.duration):'时长未提供'}</span><span>${l.slides?.length||0} 页课件</span>${l.is_demo?'<span class="demo-badge">示例资料 · 非真实课堂</span>':''}`;
  $('#lecture-source').hidden=!safeUrl(l.source_url);$('#summary-content').innerHTML=l.summary?markdown(l.summary):'<p>尚未生成整节概要。点击「整理课堂」，将按每页材料生成知识点与概要。</p>';
  $('#analyze-button').disabled=!![...S.jobs.values()].find(j=>j.lectureId===l.id&&j.running);
  const count=(l.slides||[]).filter(s=>s.reviewed).length;
  $('#coverage-label').textContent=`已学习 ${count} / ${l.slides?.length||0} 页 · 原始材料保存在本机`;
  renderSlide();renderJob();
}
function renderSlide() {
  const slide=currentSlide();const total=S.lecture?.slides?.length||0;
  $('#slide-position').textContent=total?`${S.slideIndex+1} / ${total}`:'暂无课件';
  $('#slide-prev').disabled=!slide||S.slideIndex<=0;$('#slide-next').disabled=!slide||S.slideIndex>=total-1;
  $('#bookmark-button').disabled=!slide;$('#review-button').disabled=!slide;
  $('#bookmark-button').classList.toggle('active',!!slide?.bookmarked);$('#bookmark-button').setAttribute('aria-pressed',String(!!slide?.bookmarked));
  $('#review-button').classList.toggle('reviewed',!!slide?.reviewed);$('#review-button').innerHTML=`${icon('check')}<span>${slide?.reviewed?'已学习':'标记已学'}</span>`;
  $('#slide-title').textContent=slide?.title||'暂无课件页';$('#slide-time').textContent=slide?`${time(slide.start)} — ${time(slide.end)}`:'';
  const img=slide?imageUrl(slide.image_url):'';
  if (img) { $('#slide-viewer').innerHTML=`<img src="${esc(img)}" alt="${esc(slide.title||`第 ${S.slideIndex+1} 页课件`)}" fetchpriority="high">`;$('#slide-viewer img').addEventListener('error',()=>renderFallback(slide,true),{once:true}); }
  else renderFallback(slide);
  renderThumbnails();renderMaterials();updateContext();
}
function renderFallback(slide,error=false) {
  if (slide?.id!==currentSlide()?.id) return;
  $('#slide-viewer').innerHTML=`<div class="slide-fallback"><small>${slide?`SLIDE ${String(S.slideIndex+1).padStart(2,'0')}`:'CLASSROOM MATERIALS'}</small><h2>${esc(slide?.title||'这节课堂还没有课件画面')}</h2><p>${esc(slide?.ocr||'可以先阅读课堂讲稿，或导入含课件图片／OCR 的资料包。')}</p>${error?'<p class="image-error">课件图片暂时无法读取。平台图片地址可能已失效，可重新同步；文字与讲稿仍可使用。</p>':''}</div>`;
}
function renderThumbnails() {
  const slides=S.lecture?.slides||[];
  const filtered=slides.map((s,i)=>({s,i})).filter(({s})=>S.filter==='all'||S.filter==='bookmarked'&&s.bookmarked||S.filter==='unreviewed'&&!s.reviewed);
  $$('[data-filter]').forEach(b=>b.classList.toggle('selected',b.dataset.filter===S.filter));
  $('#slide-thumbnails').innerHTML=filtered.length?filtered.map(({s,i})=>`<button class="thumbnail ${i===S.slideIndex?'selected':''}" data-slide-index="${i}" aria-label="第 ${i+1} 页 ${esc(s.title)} ${time(s.start)}" aria-current="${i===S.slideIndex?'true':'false'}"><div class="thumb-picture">${imageUrl(s.image_url)?`<img src="${esc(imageUrl(s.image_url))}" alt="" loading="lazy">`:`<span class="thumb-label">${esc(s.title||s.ocr||'课堂课件')}</span>`}<span class="thumb-number">${String(i+1).padStart(2,'0')}</span>${s.bookmarked?`<span class="thumb-bookmark">${icon('bookmark')}</span>`:''}${s.reviewed?`<span class="thumb-reviewed">${icon('check')}</span>`:''}</div><div class="thumb-time"><span>${time(s.start)}</span><span>${i+1}</span></div></button>`).join(''):'<div class="filter-empty">这个筛选下还没有课件页。</div>';
  $$('.thumb-picture img').forEach(img=>img.addEventListener('error',()=>{const wrapper=img.parentElement;img.remove();const label=document.createElement('span');label.className='thumb-label';label.textContent='课件图片暂不可用';wrapper.prepend(label);},{once:true}));
}
function renderMaterials() {
  const slide=currentSlide();const el=$('#material-content');
  $$('[data-tab]').forEach(b=>{b.classList.toggle('selected',b.dataset.tab===S.tab);b.setAttribute('aria-selected',String(b.dataset.tab===S.tab));b.setAttribute('tabindex',b.dataset.tab===S.tab?'0':'-1');});
  el.setAttribute('aria-labelledby',`tab-${S.tab}`);$('#transcript-count').textContent=slide?.transcript?.length||'';
  const dirty=slide&&S.drafts.has(slide.id)&&S.drafts.get(slide.id)!==(S.savedNotes.get(slide.id)||'');$('#note-dot').hidden=!dirty;
  $('#material-status').textContent=slide?(S.tab==='transcript'?'平台转写 · 请核对关键术语':S.tab==='notes'?(dirty?'待保存':'本地保存'):'当前页学习线索'):'';
  const warnings=(S.lecture?.warnings||[]).map(x=>String(x));
  const warningHtml=warnings.length?`<div class="notice warning">${warnings.map(esc).join('<br>')}</div>`:'';
  if(!slide){el.innerHTML=warningHtml+emptyMaterial('本节没有课件页','可阅读整节概要，或重新导入含课堂 slides 的资料。');return;}
  if(S.tab==='knowledge'){
    const knowledge=slide.knowledge||[];
    el.innerHTML=warningHtml+(knowledge.length?`<div class="knowledge-list">${knowledge.map((k,i)=>`<article class="knowledge-item"><span class="knowledge-number">${String(i+1).padStart(2,'0')}</span><div><h3>${esc(typeof k==='string'?k:k.title||'知识点')}</h3><div class="prose">${markdown(typeof k==='string'?'':k.detail||k.content||'')}</div>${k.source?`<div class="knowledge-source">${esc(k.source)}</div>`:''}</div></article>`).join('')}</div>`:emptyMaterial('知识点，等你一起整理','点击「整理课堂」，根据这页课件与对应讲稿提取概念、推导与例题。不会用示意内容替代真实课堂。','整理当前课堂','analyze'))+(slide.ocr?`<details class="ocr-details"><summary>查看课件原始文字（OCR）</summary><p>${esc(slide.ocr)}</p></details>`:'');
  }else if(S.tab==='transcript'){
    el.innerHTML=warningHtml+`<div class="transcript-notice">老师讲稿（平台转写） · ${time(slide.start)}—${time(slide.end)}<br>按课件展示时间关联，跨页语句可能在相邻页重复；自动识别的公式与专有名词请结合 slide 核对。</div>`+(slide.transcript?.length?slide.transcript.map(seg=>`<div class="transcript-line"><span class="transcript-time">${time(seg.start)}</span><p>${esc(seg.text)}</p></div>`).join(''):emptyMaterial('这个时段没有可用讲稿','可能是平台尚未生成字幕，或导入的资料没有覆盖这个时间段。你仍可以阅读课件原文并记录笔记。'));
  }else{
    const value=S.drafts.has(slide.id)?S.drafts.get(slide.id):slide.notes||'';
    el.innerHTML=`<label class="sr-only" for="slide-note">当前页个人笔记</label><textarea id="slide-note" class="note-textarea" placeholder="用自己的话，把这一页记下来。支持 Markdown…" maxlength="100000">${esc(value)}</textarea><div class="note-toolbar"><span id="note-save-status">${dirty?'有未保存的修改':'笔记保存在本机 · 支持 Markdown'}</span><button class="button subtle tiny" id="save-note">${icon('check')}保存笔记</button></div>`;
    $('#slide-note').addEventListener('input',e=>{S.drafts.set(slide.id,e.target.value);$('#note-dot').hidden=false;$('#material-status').textContent='待保存';$('#note-save-status').textContent='有未保存的修改';});
  }
}
function emptyMaterial(title,detail,button='',action='') { return `<div class="material-empty"><span data-icon="${S.tab==='transcript'?'align-left':'layers'}">${icon(S.tab==='transcript'?'align-left':'layers')}</span><div><h3>${esc(title)}</h3><p>${esc(detail)}</p>${button?`<button class="button subtle tiny" data-action="${action}">${icon('sparkles')}${esc(button)}</button>`:''}</div></div>`; }
async function selectSlide(index) { if(!S.lecture?.slides?.[index])return; if(index===S.slideIndex)return;cancelChat();S.slideIndex=index;renderSlide();remember();$('#slide-thumbnails .selected')?.scrollIntoView({block:'nearest',inline:'nearest'});await loadHistory(); }
async function patchSlide(changes) {
  const slide=currentSlide();if(!slide)return;const id=slide.id;
  try { const result=await api(`/api/slides/${encodeURIComponent(id)}`,{method:'PATCH',body:changes});Object.assign(slide,changes,result.slide||{});renderSlide();const count=S.lecture.slides.filter(s=>s.reviewed).length;const summary=S.lectures.find(l=>l.id===S.lecture.id);if(summary)summary.reviewed_count=count;renderLibrary();$('#coverage-label').textContent=`已学习 ${count} / ${S.lecture.slides.length} 页 · 原始材料保存在本机`; }catch(e){toast(e.message,'error');}
}
async function saveNote() {
  const slide=currentSlide();if(!slide)return;const id=slide.id,value=S.drafts.has(id)?S.drafts.get(id):slide.notes||'';
  const button=$('#save-note');if(button)button.disabled=true;
  try{await api(`/api/slides/${encodeURIComponent(id)}`,{method:'PATCH',body:{notes:value}});slide.notes=value;S.savedNotes.set(id,value);if(S.drafts.get(id)===value)S.drafts.delete(id);if(currentSlide()?.id===id&&S.tab==='notes')renderMaterials();toast('这一页的笔记已保存');}
  catch(e){toast(`笔记未保存：${e.message}`,'error');if(currentSlide()?.id===id&&$('#save-note'))$('#save-note').disabled=false;}
}
function renderModelStatus() { $('#chat-model-status').textContent=S.settings.model?`${S.settings.model} · ${S.settings.api_key_set?'已连接配置':'需配置 API'}`:'配置模型，开始有依据的对话'; }
function updateContext() { const slide=currentSlide();$('#context-label').innerHTML=`${icon(S.scope==='course'?'book':'layers')}<span>${esc(!S.lecture?'选择课堂后，关联学习资料':S.scope==='slide'?`第 ${S.slideIndex+1} 页 · ${slide?.title||'暂无课件'}`:S.scope==='lecture'?S.lecture.title:S.lecture.course_title||'当前课程')}</span>`;$$('[data-scope]').forEach(b=>b.classList.toggle('selected',b.dataset.scope===S.scope));$('#chat-input').disabled=!S.lecture;$('#chat-send').disabled=!S.lecture||S.chatBusy; }
function renderChatWelcome() {
  $('#chat-messages').innerHTML=`<div class="chat-welcome"><div class="assistant-greeting">从一个好问题开始<span style="color:var(--accent)">。</span></div><p>${S.lecture?'我会从所选范围的课件和讲稿中找依据，陪你把概念、推导和例题串起来。':'导入课堂后，选中一页 slide，就能围绕老师的讲解继续提问。'}</p><div class="chat-suggestions"><button data-question="帮我梳理这部分的核心概念和它们之间的关系。">这里的核心概念是什么？${icon('arrow-up-right')}</button><button data-question="结合老师的讲稿，用一个直观的例子解释这部分内容，并标注来源。">换一个例子，帮我理解${icon('arrow-up-right')}</button><button data-question="根据这些课程资料出两道自测题，暂时不要给出答案。">出两道题，检验理解${icon('arrow-up-right')}</button></div><div class="chat-grounding">${icon('shield')}<span>保留原始依据<br>资料不足时会明确说明，不将模型补充当作老师原话。</span></div>${!S.settings.api_key_set?'<button class="button subtle" data-action="settings" style="margin-top:17px">配置我的模型 API</button>':''}</div>`;
}
function sourceHtml(s,i) { return `<button class="source-chip" data-source="${i}" title="${esc(s.text||s.title)}">${icon('link')}<span>${esc(s.id||`来源 ${i+1}`)} · ${esc(s.title||'课堂资料')}${s.start!==undefined?` · ${time(s.start)}`:''}</span></button>`; }
function renderMessages(scroll=true) {
  if(!S.messages.length){renderChatWelcome();return;}
  $('#chat-messages').innerHTML=S.messages.map((m,i)=>m.role==='user'?`<div class="message user">${esc(m.content)}</div>`:`<article class="message assistant ${m.streaming?'streaming':''} ${m.error?'error':''}" data-message="${i}"><div class="message-label">${icon('sparkles')}SYNAPSE</div><div class="prose">${markdown(m.content||(!m.error?'正在查找课堂依据…':''))}</div>${m.sources?.length?`<div class="message-sources">${m.sources.map(sourceHtml).join('')}</div>`:''}</article>`).join('');
  if(scroll)$('#chat-messages').scrollTop=$('#chat-messages').scrollHeight;
}
function cancelChat() { S.chatSequence++;S.chatController?.abort();S.chatController=null;S.chatBusy=false;inlineError('','#chat-error'); }
async function loadHistory() {
  const seq=++S.chatSequence,key=contextKey();S.messages=[];renderChatWelcome();updateContext();if(!S.lecture)return;
  try{const data=await api(`/api/chat?${contextQuery()}`);if(seq!==S.chatSequence||contextKey()!==key)return;S.messages=(data.messages||[]).filter(m=>['user','assistant'].includes(m.role));renderMessages();}
  catch(e){if(seq===S.chatSequence)inlineError(`历史对话暂时无法读取：${e.message}`,'#chat-error');}
}
async function sendChat(message) {
  const text=String(message||'').trim();if(!text||S.chatBusy)return;if(!S.lecture){toast('先导入或选择一节课堂','error');return;}
  if(!S.settings.model){openSettings();toast('先配置用于提问的模型','error');return;}
  S.chatBusy=true;const seq=++S.chatSequence,key=contextKey();const controller=new AbortController();S.chatController=controller;inlineError('','#chat-error');
  const request={lecture_id:S.lecture.id,slide_id:S.scope==='slide'?currentSlide()?.id:null,scope:S.scope,message:text};
  S.messages.push({role:'user',content:text});const answer={role:'assistant',content:'',sources:[],streaming:true};S.messages.push(answer);$('#chat-input').value='';updateContext();renderMessages();
  try{
    const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request),signal:controller.signal});
    if(!response.ok){const err=await response.json().catch(()=>({}));throw new Error(err.error||err.message||`请求失败（${response.status}）`);}
    if(!response.body)throw new Error('浏览器无法读取流式响应');
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',doneEvent=false;
    const event=line=>{if(!line.trim())return;let obj;try{obj=JSON.parse(line.replace(/^data:\s?/,''));}catch{throw new Error('模型响应格式异常，请重试');}if(obj.type==='error')throw new Error(obj.message||obj.error||'模型调用失败');if(obj.type==='sources')answer.sources=obj.sources||[];if(obj.type==='delta')answer.content+=obj.text||'';if(obj.type==='done')doneEvent=true;if(obj.answer&&!answer.content)answer.content=obj.answer;};
    while(true){const chunk=await reader.read();if(chunk.done)break;buffer+=decoder.decode(chunk.value,{stream:true});let newline;while((newline=buffer.indexOf('\n'))!==-1){event(buffer.slice(0,newline));buffer=buffer.slice(newline+1);}if(seq===S.chatSequence&&contextKey()===key)renderMessages();}
    buffer+=decoder.decode();if(buffer.trim())event(buffer);if(!doneEvent)throw new Error('连接提前中断，回答可能不完整，请重试');
    answer.streaming=false;if(!answer.content)answer.content='模型没有生成正文。请检查输出额度和所选模型。';
  }catch(e){answer.streaming=false;if(e.name==='AbortError')return;answer.error=true;answer.content=answer.content?`${answer.content}\n\n> 回答中断：${e.message}`:e.message;if(seq===S.chatSequence)inlineError('本次回答未完整完成。可以重试，或检查模型设置。','#chat-error');}
  finally{if(seq===S.chatSequence&&contextKey()===key){S.chatBusy=false;S.chatController=null;renderMessages();updateContext();}}
}
async function navigateSource(messageIndex,sourceIndex) { const source=S.messages[messageIndex]?.sources?.[sourceIndex];if(!source)return;if(source.lecture_id){await loadLecture(source.lecture_id,source.slide_id);if(!source.slide_id&&Number.isFinite(Number(source.start))){const i=S.lecture.slides.findIndex(s=>Number(s.start)<=Number(source.start)&&Number(s.end)>Number(source.start));if(i>=0)await selectSlide(i);}S.tab='transcript';renderMaterials();$('#slide-viewer').scrollIntoView({block:'center',behavior:'smooth'});} }

async function startAnalysis() {
  if(!S.lecture)return;if(!S.settings.model){openSettings();toast('先配置整理课堂使用的模型','error');return;}
  try{const data=await api('/api/analyze',{method:'POST',body:{lecture_id:S.lecture.id}});trackJob(data.job_id,S.lecture.id,'整理课堂');}
  catch(e){toast(e.message,'error');}
}
function trackJob(jobId,lectureId,label) { if(!jobId){toast('服务器没有返回处理任务编号','error');return;}S.jobs.set(jobId,{id:jobId,lectureId,label,running:true,status:'running',progress:0,message:'正在准备资料…'});renderJob();if(lectureId===S.lecture?.id)$('#analyze-button').disabled=true;pollJob(jobId); }
async function pollJob(id) {
  const entry=S.jobs.get(id);if(!entry)return;
  try{const job=await api(`/api/jobs/${encodeURIComponent(id)}`);Object.assign(entry,job);entry.running=['running','pending','queued'].includes(job.status);renderJob();
    if(entry.running){setTimeout(()=>pollJob(id),1300);return;}
    if(job.status==='complete'||job.status==='completed'){
      const lectureId=job.result?.lecture_id||entry.lectureId;toast(`${entry.label}已完成`);await loadState();if(lectureId&&(!entry.lectureId||S.lecture?.id===entry.lectureId))await loadLecture(lectureId,currentSlide()?.id);
    }else{entry.status='failed';entry.error=job.error||job.message||'处理失败';toast(`${entry.label}未完成：${entry.error}`,'error');if(S.lecture?.id===entry.lectureId){const slideId=currentSlide()?.id;await loadLecture(entry.lectureId,slideId);}}
    renderJob();
  }catch(e){entry.running=false;entry.status='failed';entry.error=`无法读取进度：${e.message}`;renderJob();toast(entry.error,'error');}
}
function renderJob() { const current=[...S.jobs.values()].reverse().find(j=>!j.lectureId||j.lectureId===S.lecture?.id);const el=$('#job-banner');el.hidden=!current;if(!current)return;const pct=Math.min(100,Math.max(0,Number(current.progress)||0)*(Number(current.progress)<=1?100:1));el.classList.toggle('error',current.status==='failed');el.innerHTML=`${current.running?'<span class="spinner"></span>':icon(current.status==='failed'?'warning':'check')}<div class="job-copy"><strong>${esc(current.label||'处理课堂')}</strong> · ${esc(current.error||current.message||'处理完成')}${current.running?`<div class="job-progress"><i style="width:${Math.max(3,pct)}%"></i></div>`:''}</div>${!current.running?`<button class="icon-button" data-dismiss-job="${esc(current.id)}" aria-label="关闭进度提示">${icon('close')}</button>`:''}`;if(S.lecture)$('#analyze-button').disabled=!![...S.jobs.values()].find(j=>j.lectureId===S.lecture.id&&j.running); }

async function openSettings() {
  try{S.settings=await api('/api/settings');}catch(e){toast(e.message,'error');return;}
  const c=S.settings;
  showModal(`${modalHeader('模型与连接','连接你的模型和 Canvas。密钥只交给本地服务保存，不写入浏览器存储。')}<form id="settings-form"><div class="modal-body"><div id="modal-error" class="inline-error" hidden></div><section class="form-section"><div class="form-section-heading">${icon('sparkles')}<h3>大模型</h3><span class="badge">${c.api_key_set?'已保存密钥':'等待配置'}</span></div><div class="form-grid"><div class="field"><label for="provider">服务提供方</label><select id="provider" name="provider"><option value="glm" ${c.provider==='glm'?'selected':''}>智谱 GLM</option><option value="openai" ${c.provider==='openai'?'selected':''}>OpenAI</option><option value="compatible" ${!['glm','openai'].includes(c.provider)?'selected':''}>OpenAI 兼容 / 本地模型</option></select></div><div class="field"><label for="protocol">接口协议</label><select id="protocol" name="protocol"><option value="chat" ${c.protocol!=='responses'?'selected':''}>Chat Completions</option><option value="responses" ${c.protocol==='responses'?'selected':''}>Responses API</option></select></div><div class="field full"><label for="api-base">API Base URL</label><input id="api-base" name="api_base" type="url" value="${esc(c.api_base||'')}" placeholder="https://open.bigmodel.cn/api/paas/v4" required><small>填写基础地址，无需添加 /chat/completions 或 /responses。</small></div><div class="field"><label for="model-name">模型名称</label><input id="model-name" name="model" value="${esc(c.model||'')}" placeholder="填写账号可用的模型 ID" maxlength="200"></div><div class="field"><label for="api-key">API Key</label><input id="api-key" name="api_key" type="password" autocomplete="new-password" placeholder="${c.api_key_set?'已保存；留空保持现有密钥':'输入你的 API Key'}"><small>更换服务域名后，请重新填写密钥。</small></div><div class="field"><label for="context-chars">单次上下文字符预算</label><input id="context-chars" name="context_chars" type="number" min="4000" max="160000" step="1000" value="${esc(c.context_chars||24000)}"><small>长课堂会分段处理。应根据所选模型容量设置。</small></div><div class="field"><label>检查配置</label><button type="button" class="button subtle" id="test-model">${icon('link')}保存并测试模型</button><small>测试会发送一条简短请求，可能产生少量 API 费用。</small></div></div>${c.api_key_set?'<label class="check-field"><input type="checkbox" name="clear_api_key"><span>移除已保存的 API Key（保存后生效）</span></label>':''}<label class="check-field"><input type="checkbox" name="send_images" ${c.send_images?'checked':''}><span>整理时发送当前 slide 图片给视觉模型<br><small>默认只发送课件文字和讲稿；开启前确认所选模型支持图片。</small></span></label></section><section class="form-section"><div class="form-section-heading">${icon('book')}<h3>上海交通大学 Canvas</h3><span class="badge">${c.canvas_token_set?'已保存 Token':'未配置'}</span></div><div class="form-grid"><div class="field"><label for="canvas-base">Canvas 地址</label><input id="canvas-base" name="canvas_base" type="url" value="${esc(c.canvas_base||'https://oc.sjtu.edu.cn')}"></div><div class="field"><label for="canvas-token">Canvas Access Token</label><input id="canvas-token" name="canvas_token" type="password" autocomplete="new-password" placeholder="${c.canvas_token_set?'已保存；留空保持现有 Token':'从 Canvas 账户设置创建'}"></div></div>${c.canvas_token_set?'<label class="check-field"><input type="checkbox" name="clear_canvas_token"><span>移除已保存的 Canvas Token（保存后生效）</span></label>':''}<p class="field-help" style="margin-top:11px">课程列表通过 Canvas Token 获取。课堂实录通过 LTI 认证读取字幕和 PPT，不下载视频。平台接口变化或课程权限可能影响获取。</p></section><section class="form-section"><div class="form-section-heading">${icon('leaf')}<h3>本地存储</h3><span class="badge">视频占用 0 B</span></div><div class="status-row"><span>图片缓存</span><strong>${bytes(S.stats.cache_bytes||0)} / ${bytes(S.stats.cache_limit_bytes||134217728)}</strong></div><div class="status-row"><span>清除缓存后，已保存的文字和笔记仍可查看</span><button type="button" class="button subtle tiny" id="clear-cache">清除图片缓存</button></div></section></div><div class="modal-footer"><span class="footer-status" id="settings-status">资料与凭证保存在本机</span><button type="button" class="button subtle" data-action="close-modal">取消</button><button class="button primary" type="submit">保存设置</button></div></form>`);
  $('#provider').addEventListener('change',()=>{const provider=$('#provider').value;if(provider==='glm'){$('#api-base').value='https://open.bigmodel.cn/api/paas/v4';$('#protocol').value='chat';}else if(provider==='openai'){$('#api-base').value='https://api.openai.com/v1';$('#protocol').value='responses';}});
  $('#settings-form').addEventListener('submit',async e=>{e.preventDefault();try{await saveSettings(true);}catch{}});
  $('#test-model').addEventListener('click',async()=>{const b=$('#test-model');b.disabled=true;try{await saveSettings(false);$('#settings-status').textContent='正在测试模型…';const r=await api('/api/settings/test',{method:'POST',body:{}});if(r.ok===false)throw new Error(r.message||'连接失败');$('#settings-status').textContent=r.message||'模型连接成功';toast('模型连接成功');}catch(e){inlineError(e.message);$('#settings-status').textContent='测试未完成';}finally{b.disabled=false;}});
  $('#clear-cache').addEventListener('click',async()=>{try{const result=await api('/api/cache/clear',{method:'POST',body:{}});toast(`已释放 ${bytes(result.freed_bytes||0)} 图片缓存`);await loadState();$('#settings-status').textContent='图片缓存已清除';}catch(e){inlineError(e.message);}});
}
async function saveSettings(close=true) {
  const form=$('#settings-form');if(!form?.reportValidity())throw new Error('请检查设置中的必填项');
  const d=new FormData(form),body={provider:d.get('provider'),protocol:d.get('protocol'),api_base:d.get('api_base'),model:d.get('model'),canvas_base:d.get('canvas_base'),context_chars:Number(d.get('context_chars')),send_images:d.get('send_images')==='on',clear_api_key:d.get('clear_api_key')==='on',clear_canvas_token:d.get('clear_canvas_token')==='on'};
  if(d.get('api_key')&&!body.clear_api_key)body.api_key=d.get('api_key');if(d.get('canvas_token')&&!body.clear_canvas_token)body.canvas_token=d.get('canvas_token');
  try{const data=await api('/api/settings',{method:'PUT',body});S.settings=data.settings||data;renderModelStatus();if(!S.messages.length)renderChatWelcome();if(close){closeModal();toast('模型与连接设置已保存');}return data;}catch(e){inlineError(e.message);throw e;}
}

function openImport(tab='canvas') {
  S.importTab=tab;
  showModal(`${modalHeader('把课堂，带到这里','只导入字幕、课件图片与文字。原视频继续留在学校平台。')}<div class="modal-tabs" role="tablist"><button class="${tab==='canvas'?'selected':''}" data-import-tab="canvas">连接 Canvas</button><button class="${tab==='json'?'selected':''}" data-import-tab="json">导入资料包</button><button class="${tab==='helper'?'selected':''}" data-import-tab="helper">从播放页导出</button></div><div class="modal-body"><div id="modal-error" class="inline-error" hidden></div><div id="import-content"></div></div><div class="modal-footer"><span class="footer-status">可重复导入更新资料，个人笔记会保留。</span><button class="button subtle" data-action="close-modal">完成</button></div>`);
  renderImportContent();
}
function renderImportContent() {
  const el=$('#import-content');
  if(S.importTab==='canvas'){
    el.innerHTML=`<div class="notice">使用你自己的 Canvas Access Token 读取有权限的课程。默认优先获取平台字幕与 slides，完全不下载视频。</div>${!S.settings.canvas_token_set?'<div class="material-empty"><span>'+icon('book')+'</span><div><h3>先连接你的 Canvas</h3><p>打开模型与连接设置，填写 Canvas Token，即可浏览课程和课堂回放。</p><button class="button primary" style="margin-top:14px" data-action="settings">配置 Canvas 连接</button></div></div>':'<button class="button primary" id="fetch-courses">'+icon('refresh')+'读取我的课程</button><div id="remote-list" class="import-pick-list"></div>'}`;
    $('#fetch-courses')?.addEventListener('click',fetchCourses);
  }else if(S.importTab==='json'){
    el.innerHTML=`<div class="notice">导入标准 JSON 资料包，将 slides、时间戳和讲稿连接起来。可从播放页导出，或按示例结构整理。<br><a class="text-button" href="/api/import-example" download>下载示例资料包与字段结构 ↗</a></div><label class="file-picker">${icon('upload')}<strong>选择 JSON 资料包</strong><small>建议小于 16 MB，图片通过 URL 引用</small><input id="bundle-file" type="file" accept=".json,application/json"></label><div class="or-label">或粘贴 JSON 内容</div><div class="field"><label class="sr-only" for="bundle-json">JSON 内容</label><textarea id="bundle-json" rows="7" placeholder='{"course": {"id": "…", "title": "…"}, "lecture": {…}, "slides": […], "transcript": […]}' spellcheck="false"></textarea></div><button class="button primary" id="import-json" style="margin-top:14px">${icon('plus')}导入并关联讲稿</button>`;
    $('#bundle-file').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;if(file.size>16*1024*1024){inlineError('资料包超过 16 MB，请拆分为单节课堂后导入。');return;}try{$('#bundle-json').value=await file.text();inlineError('');}catch(err){inlineError(err.message);}});
    $('#import-json').addEventListener('click',async()=>{const b=$('#import-json');b.disabled=true;try{let bundle;try{bundle=JSON.parse($('#bundle-json').value);}catch{throw new Error('JSON 格式有误，请检查内容或选择正确的资料包。');}const result=await api('/api/import',{method:'POST',body:{bundle}});await loadState();await loadLecture(result.lecture_id||result.lecture?.id||result.id);closeModal();toast('课堂已导入，讲稿已按课件时间关联');}catch(e){inlineError(e.message);}finally{b.disabled=false;}});
  }else{
    el.innerHTML=`<div class="notice">已有播放页登录状态时，可以用项目附带的浏览器导出脚本获取字幕与 slides。脚本只读取当前课堂，不下载视频。</div><div class="helper-steps"><div class="helper-step"><span>1</span><div><strong>在浏览器打开课堂实录</strong>进入有权限访问的课程回放，选中要整理的课堂。</div></div><div class="helper-step"><span>2</span><div><strong>运行浏览器导出助手</strong>按仓库文档使用导出脚本，保留课件时间、图片地址与原始转写。登录凭证无需粘贴到资料包中。</div></div><div class="helper-step"><span>3</span><div><strong>回到这里导入资料包</strong>选择「导入资料包」，将导出的 JSON 导入并开始整理。</div></div></div><a class="button subtle" href="/browser-export" target="_blank" rel="noopener">${icon('external')}打开浏览器导出指南</a><p class="field-help" style="margin-top:14px">学校页面改版时，导出助手也可能需要更新；若脚本无法识别当前页，可使用 Canvas 连接导入。</p>`;
  }
}
async function fetchCourses() { const b=$('#fetch-courses');if(b)b.disabled=true;$('#remote-list').innerHTML='<div class="load-state"><span class="spinner"></span>正在读取课程…</div>';try{const data=await api('/api/canvas/courses',{method:'POST',body:{}});const list=data.courses||[];$('#remote-list').innerHTML=list.length?list.map(c=>`<button class="remote-card" data-remote-course="${esc(c.id)}">${icon('book')}<div><strong>${esc(c.title||c.name)}</strong><small>${esc([c.teacher,c.term].filter(Boolean).join(' · ')||`课程 ${c.id}`)}</small></div>${icon('chevron-right')}</button>`).join(''):'<p class="field-help">未发现可访问的课程，请检查学期和 Token 权限。</p>';}catch(e){inlineError(e.message);$('#remote-list').innerHTML='';}finally{if(b)b.disabled=false;} }
async function fetchLectures(courseId) { const el=$('#remote-list');if(!el)return;el.innerHTML='<div class="load-state"><span class="spinner"></span>正在读取课程回放…</div>';try{const data=await api('/api/canvas/lectures',{method:'POST',body:{course_id:courseId}});const list=data.lectures||[];if(!$('#remote-list'))return;$('#remote-list').innerHTML=`<button class="text-button" id="back-courses">← 返回课程列表</button>`+(list.length?list.map(l=>`<button class="remote-card" data-remote-lecture="${esc(l.id)}" data-remote-course-id="${esc(courseId)}">${icon('file')}<div><strong>${esc(l.title||l.name||'课堂回放')}</strong><small>${esc(l.date||l.begin||'')}${l.duration?` · ${duration(l.duration)}`:''}</small></div>${icon('download')}</button>`).join(''):'<p class="field-help">这门课程暂时没有可读取的回放。可能尚未开放点播，或平台接口发生变化。</p>');$('#back-courses')?.addEventListener('click',fetchCourses);}catch(e){inlineError(e.message);if($('#remote-list'))$('#remote-list').innerHTML='<button class="button subtle" id="retry-courses">返回课程列表</button>';$('#retry-courses')?.addEventListener('click',fetchCourses);} }
async function importRemote(courseId,lectureId,button) {button.disabled=true;inlineError('');try{const data=await api('/api/canvas/import',{method:'POST',body:{course_id:courseId,lecture_id:lectureId}});closeModal();trackJob(data.job_id,null,'导入课堂');toast('已开始导入字幕与课件，原视频不会下载');}catch(e){inlineError(e.message);button.disabled=false;} }
async function loadDemo() { const b=$('#demo-button');b.disabled=true;try{const r=await api('/api/demo',{method:'POST',body:{}});await loadState();await loadLecture(r.lecture_id||r.id);toast('已打开示例课程；内容是合成示例，不代表真实课堂');}catch(e){toast(e.message,'error');}finally{b.disabled=false;} }

function openSearch() {showModal(`${modalHeader('搜索课堂资料','在已导入的课件、知识点、讲稿和笔记中查找。')}<div class="modal-body"><div class="search-input-wrap">${icon('search')}<input id="search-query" placeholder="例如：cutsize、划分平衡、老师的例子…" autocomplete="off"></div><label class="check-field"><input id="search-course" type="checkbox" ${S.courseId?'checked':''} ${!S.courseId?'disabled':''}><span>仅搜索当前课程</span></label><div id="search-results" class="search-results"><div class="field-help">输入关键词后搜索。中文与英文术语都可以。</div></div></div>`);$('#search-query').focus();let timer;const run=()=>{clearTimeout(timer);timer=setTimeout(searchMaterials,300);};$('#search-query').addEventListener('input',run);$('#search-course').addEventListener('change',run);}
async function searchMaterials() {const input=$('#search-query');if(!input)return;const q=input.value.trim(),seq=++S.searchSequence;if(!q){$('#search-results').innerHTML='<p class="field-help">输入关键词后搜索。</p>';return;}try{const params=new URLSearchParams({q});if($('#search-course').checked&&S.courseId)params.set('course_id',S.courseId);const data=await api(`/api/search?${params}`);if(seq!==S.searchSequence||!$('#search-results'))return;const hits=data.results||[];$('#search-results').innerHTML=hits.length?hits.map(r=>`<button class="search-result" data-search-lecture="${esc(r.lecture_id)}" data-search-slide="${esc(r.slide_id||'')}"><strong>${esc(r.title||'课堂资料')}</strong><small>${esc(r.lecture_title||'')} ${r.start!==undefined?`· ${time(r.start)}`:''}</small><p>${esc(r.snippet||r.text||'')}</p></button>`).join(''):'<div class="material-empty"><span>'+icon('search')+'</span><div><h3>暂时没有找到</h3><p>试试更短的关键词，或切换到全部课程。</p></div></div>';}catch(e){if($('#search-results'))$('#search-results').innerHTML=`<div class="inline-error">${esc(e.message)}</div>`;} }
function openExport() {if(!S.lecture)return;const id=encodeURIComponent(S.lecture.id);showModal(`${modalHeader('带走你的学习成果',S.lecture.title)}<div class="modal-body"><div class="export-options"><a class="export-card" href="/api/export/${id}?format=markdown" download>${icon('file')}<div><strong>Markdown 笔记</strong><small>知识点、讲稿、个人笔记与来源，方便继续编辑。</small></div></a><a class="export-card" href="/api/export/${id}?format=json" download>${icon('code')}<div><strong>完整 JSON 资料包</strong><small>保留课件、转写时间戳和学习进度，方便备份与迁移。</small></div></a></div></div>`);}
async function showStorage() {try{await loadState();}catch{}const st=S.stats;showModal(`${modalHeader('轻装学习，本地保存','课堂视频不会下载到本机。仅保存文字、学习记录和按需读取的课件图片。')}<div class="modal-body"><div class="status-row"><span>课程</span><strong>${S.courses.length} 门</strong></div><div class="status-row"><span>课堂</span><strong>${S.lectures.length} 节</strong></div><div class="status-row"><span>课件图片缓存</span><strong>${bytes(st.cache_bytes||0)}</strong></div><div class="storage-meter"><i style="width:${Math.min(100,100*(st.cache_bytes||0)/(st.cache_limit_bytes||134217728))}%"></i></div><p class="field-help">图片缓存设有容量上限，可在设置中清除。个人笔记和平台原文会保存在 SQLite 数据库中；建议定期导出 JSON 资料包备份。</p><button class="button subtle" data-action="settings" style="margin-top:18px">管理模型与本地存储</button></div>`);}

document.addEventListener('click', async e=>{
  const b=e.target.closest('button,a');if(!b)return;
  if(b.dataset.action==='close-modal')closeModal();
  if(b.dataset.action==='reload')location.reload();
  if(b.dataset.action==='settings')await openSettings();
  if(b.dataset.action==='analyze')await startAnalysis();
  if(b.dataset.course){cancelChat();S.courseId=b.dataset.course;renderLibrary();const first=S.lectures.find(l=>String(l.course_id)===String(S.courseId));if(first)await loadLecture(first.id);else renderEmpty();}
  if(b.dataset.lecture)await loadLecture(b.dataset.lecture);
  if(b.dataset.slideIndex!==undefined)await selectSlide(Number(b.dataset.slideIndex));
  if(b.dataset.tab){S.tab=b.dataset.tab;renderMaterials();}
  if(b.dataset.filter){S.filter=b.dataset.filter;renderThumbnails();}
  if(b.dataset.scope&&S.scope!==b.dataset.scope){cancelChat();S.scope=b.dataset.scope;updateContext();await loadHistory();}
  if(b.dataset.question){$('#chat-input').value=b.dataset.question;$('#chat-input').focus();}
  if(b.dataset.source!==undefined)await navigateSource(Number(b.closest('[data-message]').dataset.message),Number(b.dataset.source));
  if(b.dataset.importTab)openImport(b.dataset.importTab);
  if(b.dataset.remoteCourse)await fetchLectures(b.dataset.remoteCourse);
  if(b.dataset.remoteLecture)await importRemote(b.dataset.remoteCourseId,b.dataset.remoteLecture,b);
  if(b.dataset.searchLecture){closeModal();await loadLecture(b.dataset.searchLecture,b.dataset.searchSlide||null);S.tab='transcript';renderMaterials();}
  if(b.dataset.dismissJob){S.jobs.delete(b.dataset.dismissJob);renderJob();}
  if(b.id==='save-note')await saveNote();
});
$('#import-button').addEventListener('click',()=>openImport());$('#welcome-import').addEventListener('click',()=>openImport());$('#demo-button').addEventListener('click',loadDemo);
$('#settings-button').addEventListener('click',openSettings);$('#storage-info').addEventListener('click',showStorage);$('#search-button').addEventListener('click',openSearch);
$('#export-button').addEventListener('click',openExport);$('#analyze-button').addEventListener('click',startAnalysis);
$('#slide-prev').addEventListener('click',()=>selectSlide(S.slideIndex-1));$('#slide-next').addEventListener('click',()=>selectSlide(S.slideIndex+1));
$('#bookmark-button').addEventListener('click',()=>patchSlide({bookmarked:!currentSlide()?.bookmarked}));$('#review-button').addEventListener('click',()=>patchSlide({reviewed:!currentSlide()?.reviewed}));
$('#lecture-source').addEventListener('click',()=>{const url=safeUrl(S.lecture?.source_url);if(url)window.open(url,'_blank','noopener,noreferrer');});
$('#chat-form').addEventListener('submit',e=>{e.preventDefault();sendChat($('#chat-input').value);});
$('#chat-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();sendChat(e.target.value);}});
$('#chat-clear').addEventListener('click',async()=>{if(!S.lecture||S.chatBusy)return;if(!S.messages.length)return;if(!confirm('清除此范围的对话记录并开始新的提问？课堂资料和笔记会保留。'))return;try{await api(`/api/chat?${contextQuery()}`,{method:'DELETE',body:{}});S.messages=[];renderChatWelcome();toast('已开始新一轮对话');}catch(e){toast(e.message,'error');}});
$('#delete-lecture').addEventListener('click',async()=>{if(!S.lecture)return;if(!confirm('移除此节课堂及其学习记录？建议先导出 JSON 备份。学校平台上的原始资料不会改变。'))return;const id=S.lecture.id;try{await api(`/api/lectures/${encodeURIComponent(id)}`,{method:'DELETE',body:{}});S.lecture=null;await loadState(true);toast('已移除本地课堂');}catch(e){toast(e.message,'error');}});
$('#modal').addEventListener('click',e=>{if(e.target===$('#modal')){const r=$('#modal').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closeModal();}});
document.addEventListener('keydown',e=>{
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openSearch();return;}
  if((e.metaKey||e.ctrlKey)&&e.key==='Enter'&&e.target.id==='slide-note'){e.preventDefault();saveNote();return;}
  if(e.target.closest('.material-tabs')&&['ArrowLeft','ArrowRight'].includes(e.key)){const tabs=['knowledge','transcript','notes'];let i=tabs.indexOf(S.tab);i=(i+(e.key==='ArrowRight'?1:2))%3;S.tab=tabs[i];renderMaterials();$(`[data-tab="${S.tab}"]`).focus();e.preventDefault();return;}
  if($('#modal').open||e.target.closest('textarea,input,select,[contenteditable=true]'))return;
  if(e.key==='ArrowLeft'){e.preventDefault();selectSlide(S.slideIndex-1);}if(e.key==='ArrowRight'){e.preventDefault();selectSlide(S.slideIndex+1);}
});
window.addEventListener('beforeunload',e=>{if([...S.drafts].some(([id,v])=>v!==(S.savedNotes.get(id)||''))){e.preventDefault();e.returnValue='';}});
function setTheme(theme) {document.documentElement.dataset.theme=theme;try{localStorage.setItem('synapse-theme',theme);}catch{}$('#theme-button').innerHTML=icon(theme==='dark'?'sun':'moon');}
$('#theme-button').addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
icons();let theme='light';try{theme=localStorage.getItem('synapse-theme')||'light';}catch{}setTheme(theme);
renderChatWelcome();updateContext();loadState(true).catch(e=>{toast(`无法连接本地服务：${e.message}`,'error');$('#course-list').innerHTML='<button class="button subtle" data-action="reload">重新连接本地服务</button>';});

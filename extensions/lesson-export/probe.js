// This function runs inside the user's current authenticated SJTU tab.
// It calls the player's existing read-only service; no token is read or exported.
// The Vue/webpack adapter is intentionally small and fails clearly on a new build.
export async function probePage(mode, requestedId) {
  try {
    if (location.hostname !== 'v.sjtu.edu.cn' || !location.hash.startsWith('#/play-center')) {
      throw new Error('请在交大课堂实录的播放页面使用导出功能。');
    }
    const app = document.getElementById('app');
    const root = app?._vnode || app?.__vue_app__?._instance?.subTree;
    if (!root) throw new Error('播放器还未加载完成，请稍后重试。');
    const queue = [root];
    const seen = new Set();
    let recordings = [];
    while (queue.length) {
      const node = queue.shift();
      if (!node || typeof node !== 'object' || seen.has(node)) continue;
      seen.add(node);
      const candidate = node.component?.props?.courseList;
      if (Array.isArray(candidate) && candidate.some(item => item?.id && item?.courBeginTime) && candidate.length > recordings.length) recordings = candidate;
      if (node.component?.subTree) queue.push(node.component.subTree);
      if (Array.isArray(node.children)) queue.push(...node.children);
      if (node.suspense?.activeBranch) queue.push(node.suspense.activeBranch);
    }
    if (!recordings.length) throw new Error('没有找到节次列表。请刷新播放页；页面更新时可改用 Canvas Token 导入。');
    const courseTitle = String(recordings[0].subjName || recordings[0].teclName || '交大课程');
    const lectures = recordings.map((recording, i) => ({
      id: String(recording.id),
      title: `${recording.courBeginTime || ''} · 第${recording.letiNumber || i + 1}节`,
      available: recording.vodClickEnable !== false,
    }));
    if (mode === 'list') return { ok: true, data: { courseTitle, lectures } };
    if (mode !== 'export') throw new Error('不支持的导出操作。');
    const recording = recordings.find(item => String(item.id) === String(requestedId));
    if (!recording || recording.vodClickEnable === false) throw new Error('所选节次不可用，请重新读取页面。');

    // Known 2026 resource-manage build. Do not scan localStorage, cookies,
    // account state, or arbitrary modules for credentials if it changes.
    const registry = globalThis.webpackChunkjy_application_resoucemanage_ui;
    if (!Array.isArray(registry)) throw new Error('播放器版本不受此导出适配器支持，请使用应用的 Canvas Token 导入。');
    let requirePlayer;
    registry.push([[Date.now()], {}, require => { requirePlayer = require; }]);
    let service;
    try { service = requirePlayer(96885); } catch (_) { /* Build ID changed. */ }
    if (typeof service?.Te !== 'function' || typeof service?.lN !== 'function') {
      throw new Error('学校播放器接口已更新。请使用 Canvas Token 导入，或向项目反馈页面版本。');
    }
    function payload(response) {
      if (response?.status !== 200) throw new Error('平台拒绝读取材料，请确认本页能正常查看语音与 PPT。');
      const data = response.data || {};
      if (data.ok === false || data.dataOk === false) throw new Error('平台返回材料读取失败，请刷新并重试。');
      return data.data && !data.docList && !data.beforeAssemblyList && !data.afterAssemblyList ? data.data : data;
    }
    const id = Number(recording.id);
    if (!Number.isSafeInteger(id)) throw new Error('节次编号格式不正确。');
    const [captionResponse, slideResponse] = await Promise.all([service.Te(id, true), service.lN({ courseId: id })]);
    function captions(data) {
      const before = data.beforeAssemblyList || [];
      return before.some(item => String(item.res || '').trim()) ? before : (data.afterAssemblyList || []);
    }
    let rawCaptions = captions(payload(captionResponse));
    if (!rawCaptions.length) rawCaptions = captions(payload(await service.Te(id, false)));
    const number = value => Number.isFinite(Number(value)) ? Math.max(0, Number(value)) : 0;
    const transcript = rawCaptions.filter(item => String(item.res || '').trim()).map(item => ({
      start: number(item.bg) / 1000,
      end: Math.max(number(item.bg), number(item.ed)) / 1000,
      text: String(item.res).trim(),
    })).sort((a, b) => a.start - b.start);
    const slides = (payload(slideResponse).docList || []).filter(item => item.showFlag !== false).map(item => {
      const ocr = String(item.ocrText || '').trim();
      const keywords = Array.isArray(item.textKeywordList) ? item.textKeywordList.map(String) : [];
      let image = '';
      try {
        const parsed = new URL(String(item.imageUrl || ''), location.origin);
        if (item.imageUrl && parsed.protocol === 'https:' && !parsed.username && !parsed.password) image = parsed.href;
      } catch (_) { /* Preserve the rest of this slide when its image is missing. */ }
      return { start: number(item.imageSeekTime), image_url: image, ocr,
        title: (ocr.split('\n').find(line => line.trim()) || keywords.slice(0, 4).join(' · ')).slice(0, 160) };
    }).sort((a, b) => a.start - b.start);
    if (!slides.length && !transcript.length) throw new Error('这一节还没有可用字幕和 PPT。不会自动下载视频。');
    const begin = String(recording.courBeginTime || '');
    const end = String(recording.courEndTime || '');
    const parsedDuration = (Date.parse(end.replace(' ', 'T')) - Date.parse(begin.replace(' ', 'T'))) / 1000;
    const duration = Math.max(Number.isFinite(parsedDuration) ? parsedDuration : 0, ...transcript.map(item => item.end), ...slides.map(item => item.start), 0);
    // Teaching-class IDs and Canvas IDs are distinct, so browser imports get a
    // separate namespace. Repeating the same export still produces stable IDs.
    let titleHash = 2166136261;
    for (const char of courseTitle) titleHash = Math.imul(titleHash ^ char.charCodeAt(0), 16777619) >>> 0;
    const classKey = recording.teclId || recording.teachingClassId || titleHash.toString(16);
    const courseId = `sjtu-browser:${classKey}`;
    const lectureId = `${courseId}:${recording.id}`;
    slides.forEach((slide, i) => Object.assign(slide, {
      id: `${lectureId}:slide:${i + 1}`, index: i + 1,
      title: slide.title || `课堂画面 ${i + 1}`, end: slides[i + 1]?.start ?? duration,
    }));
    const warnings = [];
    if (!transcript.length) warnings.push('平台暂无讲稿；只导出了课堂画面。');
    if (!slides.length) warnings.push('平台暂无 slides；只导出了讲稿。');
    const teachers = recording.teclTeacNames || recording.teacNames || [];
    return { ok: true, data: {
      version: 1,
      course: { id: courseId, title: courseTitle, teacher: String(recording.tecName || (Array.isArray(teachers) ? teachers.join(', ') : teachers)), term: '' },
      lecture: { id: lectureId, course_id: courseId, platform_id: String(recording.id), title: lectures.find(item => item.id === String(recording.id)).title,
        date: begin.slice(0, 10), duration, warnings,
        source_url: 'https://v.sjtu.edu.cn/jy-application-resourcemanage-ui/#/play-center' },
      slides, transcript, warnings,
    } };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : '读取材料失败。' };
  }
}

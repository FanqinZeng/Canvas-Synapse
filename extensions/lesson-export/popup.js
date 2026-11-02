import { probePage } from './probe.js';

const el = id => document.getElementById(id);
let page = null;
let tabId = null;

function status(message, error = false) {
  el('status').textContent = message;
  el('status').classList.toggle('error', error);
}

async function probe(mode, id) {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  if (!tab?.id || !tab.url?.startsWith('https://v.sjtu.edu.cn/jy-application-resourcemanage-ui/')) {
    throw new Error('请先打开已登录的交大课堂实录播放页，再点击扩展图标。');
  }
  if (tabId !== null && tabId !== tab.id && mode !== 'list') throw new Error('当前页面已切换，请重新读取节次。');
  tabId = tab.id;
  const result = await chrome.scripting.executeScript({
    target: { tabId: tab.id }, world: 'MAIN', func: probePage, args: [mode, id]
  });
  if (!result[0]?.result?.ok) throw new Error(result[0]?.result?.error || '读取失败，请刷新课程页重试。');
  return result[0].result.data;
}

el('load').addEventListener('click', async () => {
  el('load').disabled = true;
  el('export').disabled = true;
  status('正在读取课堂节次…');
  try {
    page = await probe('list', null);
    el('lecture').replaceChildren();
    page.lectures.forEach(item => {
      const option = document.createElement('option');
      option.value = item.id;
      option.textContent = item.title + (item.available ? '' : ' · 尚未开放');
      option.disabled = !item.available;
      el('lecture').append(option);
    });
    el('lecture').value = page.lectures.find(item => item.available)?.id || '';
    el('lecture').disabled = false;
    el('course').value = page.courseTitle;
    el('export').disabled = !el('lecture').value;
    status(`已读取 ${page.lectures.length} 节。选择后导出一节，不会下载音视频。`);
  } catch (error) {
    status(error.message, true);
  } finally {
    el('load').disabled = false;
  }
});

el('export').addEventListener('click', async () => {
  el('export').disabled = true;
  status('正在获取讲稿与 slides 索引，请保持弹窗打开…');
  try {
    const bundle = await probe('export', el('lecture').value);
    const courseName = el('course').value.trim();
    if (courseName) bundle.course.title = courseName;
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${bundle.lecture.date || 'lecture'}-${bundle.lecture.platform_id}-synapse.json`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    status(`已导出 ${bundle.slides.length} 张画面、${bundle.transcript.length} 段讲稿。${(bundle.warnings || []).join(' ')}`);
  } catch (error) {
    status(error.message, true);
  } finally {
    el('export').disabled = false;
  }
});

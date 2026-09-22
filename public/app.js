import { MIN_YEAR, MAX_YEAR, monthCells, monthMembers } from './calendar.js';
const $ = id => document.getElementById(id);
const now = new Date();
let year = Math.max(MIN_YEAR, Math.min(MAX_YEAR, now.getFullYear()));
let month = now.getMonth() + 1;
let members = [], groups = [], selected = new Set(), selectedDay = null, version = null;
let loaded = false;
const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};
const tone = group => `tone-${Math.max(0, groups.indexOf(group)) % 4}`;
for (let y = MIN_YEAR; y <= MAX_YEAR; y++) $('year').add(new Option(`${y} 年`, y));
for (let m = 1; m <= 12; m++) $('month').add(new Option(`${m} 月`, m));
function renderGroups() {
  $('groups').replaceChildren(...groups.map(group => {
    const button = el('button', 'chip');
    button.type = 'button';
    button.setAttribute('aria-pressed', selected.has(group));
    const check = el('span', 'check', '✓'); check.setAttribute('aria-hidden', 'true');
    button.append(check, el('span', '', group), el('span', 'chip-count', members.filter(m => m.group === group).length));
    button.onclick = () => { selected.has(group) ? selected.delete(group) : selected.add(group); render(); };
    return button;
  }));
}
function render() {
  renderGroups();
  $('year').value = year; $('month').value = month;
  $('month-title').textContent = `${year} 年 ${String(month).padStart(2, '0')} 月`;
  $('month-en').textContent = new Date(year, month - 1, 1).toLocaleString('en', { month: 'long' }).toUpperCase();
  $('prev').disabled = year === MIN_YEAR && month === 1;
  $('next').disabled = year === MAX_YEAR && month === 12;
  const visible = monthMembers(members, selected, year, month);
  $('month-count').textContent = loaded ? visible.length : '—';
  $('selection-note').textContent = !loaded ? '正在读取数据' : selected.size ? `已选 ${selected.size} 个职能组 · 点击日期查看` : '请选择至少一个职能组';
  $('calendar').replaceChildren(...monthCells(year, month).map(cell => {
    const day = el(cell.current ? 'button' : 'div', `day${cell.current ? '' : ' outside'}`);
    day.append(el('span', 'date-number', cell.day));
    if (!cell.current) { day.setAttribute('aria-hidden', 'true'); return day; }
    day.type = 'button';
    const birthdays = visible.filter(m => m.displayDay === cell.day);
    day.setAttribute('aria-label', `${month}月${cell.day}日，${birthdays.length}位成员生日${birthdays.length ? '：' + birthdays.map(m => m.name).join('、') : ''}`);
    day.setAttribute('aria-pressed', selectedDay === cell.day);
    if (year === now.getFullYear() && month === now.getMonth() + 1 && cell.day === now.getDate()) { day.classList.add('today'); day.setAttribute('aria-current', 'date'); }
    if (selectedDay === cell.day) day.classList.add('selected');
    birthdays.slice(0, 2).forEach(m => {
      const event = el('span', `event ${tone(m.group)}`);
      event.title = `${m.name} · ${m.group}`;
      event.append(el('i'), document.createTextNode(m.name)); day.append(event);
    });
    if (birthdays.length > 2) day.append(el('span', 'more', `+${birthdays.length - 2} 位`));
    if (birthdays.length) day.append(el('span', 'mobile-badge', `${birthdays.length} 位生日`));
    day.onclick = () => { selectedDay = selectedDay === cell.day ? null : cell.day; render(); };
    return day;
  }));
  $('agenda-title').textContent = selectedDay === null ? '本月生日' : `${month} 月 ${selectedDay} 日的生日`;
  $('show-month').hidden = selectedDay === null;
  const agenda = selectedDay === null ? visible : visible.filter(m => m.displayDay === selectedDay);
  $('agenda-count').textContent = `${agenda.length} 位成员`;
  $('agenda-list').replaceChildren(...agenda.map(m => {
    const card = el('article', 'member');
    const date = el('div', 'member-date');
    date.append(el('strong', '', String(m.displayDay).padStart(2, '0')), el('span', '', `${month} 月`));
    const info = el('div', 'member-info'), group = el('div', `member-group ${tone(m.group)}`);
    group.append(el('i'), document.createTextNode(m.group));
    info.append(el('div', 'member-name', m.name), group);
    if (m.shifted) info.append(el('div', 'leap-note', '原生日 2 月 29 日'));
    card.append(date, info); return card;
  }));
  if (!agenda.length) {
    const empty = el('div', 'empty');
    empty.append(el('p', '', !loaded ? '生日数据暂未加载' : !selected.size ? '选一个职能组，看看大家的生日吧' : selectedDay === null ? '所选职能组本月暂无生日' : '这一天暂无符合筛选条件的生日'));
    $('agenda-list').append(empty);
  }
}
function navigate(delta) {
  const d = new Date(year, month - 1 + delta, 1);
  if (d.getFullYear() < MIN_YEAR || d.getFullYear() > MAX_YEAR) return;
  year = d.getFullYear(); month = d.getMonth() + 1; selectedDay = null; render();
}
$('prev').onclick = () => navigate(-1); $('next').onclick = () => navigate(1);
$('year').onchange = e => { year = Number(e.target.value); selectedDay = null; render(); };
$('month').onchange = e => { month = Number(e.target.value); selectedDay = null; render(); };
$('today').onclick = () => { const today = new Date(); year = Math.max(MIN_YEAR, Math.min(MAX_YEAR, today.getFullYear())); month = today.getMonth() + 1; selectedDay = null; render(); };
$('all').onclick = () => { selected = new Set(groups); render(); };
$('none').onclick = () => { selected.clear(); render(); };
$('show-month').onclick = () => { selectedDay = null; render(); };
async function refresh() {
  try {
    const response = await fetch('./data/birthdays.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('数据读取失败');
    const data = await response.json();
    if (!Array.isArray(data.members) || !Array.isArray(data.groups) || !data.version) throw new Error('数据格式不正确');
    $('load-error').hidden = true;
    if (version !== data.version) {
      const allSelected = !loaded || selected.size === groups.length;
      members = data.members; groups = data.groups;
      selected = allSelected ? new Set(groups) : new Set([...selected].filter(g => groups.includes(g)));
      version = data.version; loaded = true; render();
    }
    const date = new Date(data.updatedAt);
    $('updated').textContent = `数据更新于 ${date.toLocaleString('zh-CN', { year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hour12:false })}`;
  } catch {
    $('updated').textContent = loaded ? '暂时无法检查更新 · 正显示上次数据' : '数据加载失败';
    if (!loaded) { $('load-error').textContent = '暂时无法读取生日数据，请检查网络。页面会自动重试。'; $('load-error').hidden = false; }
  }
}
render(); refresh();
setInterval(() => { if (!document.hidden) refresh(); }, 30000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });

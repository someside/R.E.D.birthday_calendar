"""Read origin.xlsx with the Python standard library; optionally publish only birthday data."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'public' / 'data' / 'birthdays.json'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def read_rows(path):
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        workbook = ET.fromstring(z.read('xl/workbook.xml'))
        props = workbook.find('s:workbookPr', NS)
        epoch1904 = props is not None and props.get('date1904') in ('1', 'true')
        sheet = workbook.find('s:sheets/s:sheet', NS)
        rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        relationships = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        target = next(x.get('Target') for x in relationships if x.get('Id') == rid)
        target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        rows = []
        for row in ET.fromstring(z.read(target)).findall('s:sheetData/s:row', NS):
            values = {}
            for cell in row.findall('s:c', NS):
                column = re.match(r'[A-Z]+', cell.get('r')).group()
                kind = cell.get('t')
                value = cell.find('s:v', NS)
                if kind == 'inlineStr':
                    inline = cell.find('s:is', NS)
                    text = ''.join(inline.itertext()) if inline is not None else ''
                elif value is None:
                    text = ''
                elif kind == 's':
                    text = strings[int(value.text)]
                else:
                    text = value.text or ''
                values[column] = text.strip()
            if any(values.values()): rows.append((int(row.get('r')), values))
        return rows, epoch1904

def parse_date(text, epoch1904=False):
    if re.fullmatch(r'\d+(?:\.\d+)?', text):
        numeric = float(text)
        if numeric < 1 or numeric > 100000: raise ValueError('Excel 日期数值超出范围')
        date = datetime(1904, 1, 1) + timedelta(days=numeric) if epoch1904 else datetime(1899, 12, 30) + timedelta(days=numeric)
        return date.year, date.month, date.day
    parts = re.fullmatch(r'(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})(?:日)?(?:[ T].*)?', text)
    if parts:
        y, m, d = map(int, parts.groups()); datetime(y, m, d); return y, m, d
    parts = re.fullmatch(r'(\d{1,2})[-/月](\d{1,2})日?', text)
    if parts:
        m, d = map(int, parts.groups()); datetime(2000, m, d); return None, m, d
    raise ValueError('日期格式无法识别，请使用 Excel 日期或 YYYY-MM-DD')

def convert(source):
    rows, epoch1904 = read_rows(source)
    if not rows: raise ValueError('表格为空')
    headers = rows[0][1]
    def field(words):
        matches = [k for k, v in headers.items() if any(w in v for w in words)]
        if len(matches) != 1: raise ValueError('无法唯一识别字段：' + '/'.join(words))
        return matches[0]
    name_col, group_col, date_col = field(['姓名']), field(['职能组']), field(['出生日期', '生日'])
    seen, members, warnings, errors = set(), [], [], []
    duplicates = 0
    for number, row in rows[1:]:
        name, group, raw = row.get(name_col, ''), row.get(group_col, ''), row.get(date_col, '')
        if not (name or group or raw): continue
        if not name or not group or not raw:
            errors.append(f'第 {number} 行：姓名、职能组或生日为空'); continue
        try: birth_year, month, day = parse_date(raw, epoch1904)
        except ValueError as exc:
            errors.append(f'第 {number} 行：{exc}'); continue
        key = tuple(sorted(row.items()))
        if key in seen: duplicates += 1; continue
        seen.add(key)
        if birth_year and datetime(birth_year, month, day).date() > datetime.now().date():
            warnings.append(f'第 {number} 行：出生日期在未来，按月日展示，请核对原表')
        members.append({'name': name, 'group': group, 'month': month, 'day': day})
    if errors: raise ValueError('\n'.join(errors) + '\n本次未更新，保留上一份有效数据。')
    if not members: raise ValueError('没有有效成员，本次不覆盖线上数据')
    members.sort(key=lambda m: (m['month'], m['day'], m['group'], m['name']))
    groups = sorted({m['group'] for m in members})
    payload = {'groups': groups, 'members': members}
    version = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    if duplicates: warnings.append(f'合并了 {duplicates} 条完全重复记录')
    return payload, version, warnings

def git(*args, check=True):
    command = ['git', '-c', f'safe.directory={ROOT.as_posix()}', '-c', 'credential.interactive=never', '-C', str(ROOT), *args]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and result.returncode: raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result

def publish():
    branch = git('branch', '--show-current').stdout.strip()
    if branch != 'main': raise RuntimeError('自动同步只允许在 main 分支运行')
    if not git('remote', 'get-url', 'origin').stdout.strip(): raise RuntimeError('未配置 GitHub origin')
    if git('ls-files', '-u').stdout.strip(): raise RuntimeError('仓库有未解决冲突，请先处理')
    # Never include unrelated staged files or local code edits in an automatic publish.
    staged = git('diff', '--cached', '--name-only').stdout.splitlines()
    if any(p != 'public/data/birthdays.json' for p in staged):
        raise RuntimeError('有其他已暂存的修改，请先完成代码提交，再自动同步')
    git('add', '--', 'public/data/birthdays.json')
    if git('diff', '--cached', '--quiet', check=False).returncode:
        git('commit', '-m', 'Update birthday calendar data', '--', 'public/data/birthdays.json')
    # Ensure an automatic retry cannot publish unrelated commits created by a human.
    git('fetch', 'origin', 'main')
    ahead = git('rev-list', 'origin/main..HEAD').stdout.splitlines()
    for commit in ahead:
        paths = git('diff-tree', '--root', '--no-commit-id', '--name-only', '-r', commit).stdout.splitlines()
        if any(p != 'public/data/birthdays.json' for p in paths):
            raise RuntimeError('存在尚未推送的代码提交，请先手动推送代码，再自动同步生日')
    git('push', 'origin', 'HEAD:main')
    print('GitHub 同步成功，等待 Cloudflare Pages 部署。', flush=True)

def sync(source, push=False):
    payload, version, warnings = convert(source)
    for warning in warnings: print('提示：' + warning, flush=True)
    previous = json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else {}
    changed = previous.get('version') != version
    if changed:
        payload.update(version=version, updatedAt=datetime.now(timezone.utc).isoformat())
        DATA.parent.mkdir(parents=True, exist_ok=True)
        temporary = DATA.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(DATA)
        print(f'已更新 {len(payload["members"])} 位成员、{len(payload["groups"])} 个职能组。', flush=True)
    else: print('生日数据未变化。', flush=True)
    if push: publish()
    return changed

def main():
    parser = argparse.ArgumentParser(description='Excel 生日数据同步')
    parser.add_argument('--source', type=Path, default=ROOT / 'origin.xlsx')
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--push', action='store_true')
    args = parser.parse_args()
    if not args.watch:
        try: sync(args.source, args.push)
        except Exception as exc: print('同步失败：' + str(exc), file=sys.stderr); return 1
        return 0
    print('正在监听 origin.xlsx；保存后稳定 5 秒再同步。按 Ctrl+C 停止。', flush=True)
    successful = None
    candidate, since, retry_after = None, 0, 0
    while True:
        try:
            stat = args.source.stat()
            stamp = (stat.st_mtime_ns, stat.st_size)
            if stamp != candidate: candidate, since = stamp, time.monotonic()
            if stamp != successful and time.monotonic() - since >= 5 and time.monotonic() >= retry_after:
                sync(args.source, args.push)
                successful = stamp
        except KeyboardInterrupt: return 0
        except Exception as exc:
            print('暂未同步：' + str(exc) + '\n将在 60 秒后重试。', flush=True)
            retry_after = time.monotonic() + 60
        time.sleep(2)

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())

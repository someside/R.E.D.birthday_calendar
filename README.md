# R.E.D. 成员生日日历

简洁的静态生日月历，适配手机与电脑。职能组支持多选，日期范围为 2020 年 1 月至 2100 年 12 月。不使用数据库、OpenAI API、外部字体或第三方页面脚本。

## 本地使用

需要 Python 3.10+，数据处理无需安装第三方库。Windows 启动脚本也会识别本机 Codex 附带的 Python。自动同步另需安装 Git，并完成 GitHub 登录。

1. 将 `origin.xlsx` 放在仓库根目录。
2. 双击 `preview.cmd`，浏览器打开 http://localhost:8788 。
3. 预览期间更新 Excel 后，另一个终端运行 `python scripts/sync.py`；页面将在约 30 秒内检查新数据。

## Cloudflare Pages 部署（GitHub 集成）

1. 在 Cloudflare 控制台创建 Pages 项目，选择“连接到 Git”。不要选择 Direct Upload。
2. 授权访问 `someside/R.E.D.birthday_calendar` 这个仓库。
3. 生产分支：`main`。
4. 框架预设：`None`；构建命令：留空；构建输出目录：`public`；根目录：仓库根目录。
5. 保存并部署，使用 Cloudflare 分配的 HTTPS `pages.dev` 地址。

只有 `public/` 进入网站。Cloudflare 构建时不读取 Excel，因为原表只保留在本地。

日历完全在浏览器端运行，使用 Pages 免费静态托管，不需要 Workers、数据库或付费服务器。当前免费套餐每月有 500 次构建额度，具体以 Cloudflare 最新政策为准。国内可用性请用实际校园网与手机网络测试。

## 日常更新

首次代码上传、GitHub 登录和 Pages 绑定完成后，双击 `sync.cmd`，保持窗口运行。修改并保存 `origin.xlsx` 后，程序等待文件稳定 5 秒，转换数据并自动提交、推送到 GitHub；Cloudflare 随后自动部署。公开页面每 30 秒检查一次数据，实际更新时间还取决于部署耗时。

也可以手动运行：

```sh
python scripts/sync.py
python scripts/sync.py --push
python scripts/sync.py --watch --push
```

- 仅数据发生变化才生成新版本，不因保存格式变化产生重复发布。
- 自动提交只包含 `public/data/birthdays.json`，不会提交其他源码修改。
- 如果有其他已暂存文件、待推送源码提交、分支冲突或远端新提交，程序会提示并停止本次发布，不会强制推送或覆盖远端。请先人工完成代码同步。
- 网络失败每 60 秒重试。电脑关闭后公开网站仍显示最后成功部署的版本；再次启动同步程序会检查当前 Excel。
- 自动同步仅在 `main` 分支运行。普通代码修改需要自行提交、推送，或交给开发助手完成。
- 这是前台监听程序，未设置开机自启。关闭窗口即停止监听。

## Excel 规则

读取第一个工作表，第一条非空行为表头，按包含“姓名”“职能组”“出生日期”或“生日”的列名识别字段。保留当前原表即可。

- 支持标准 Excel 日期、`YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY年M月D日`、`M月D日`、`M/D`。
- 使用公历月日逐年显示。2 月 29 日在平年显示于 2 月 28 日并注明原生日；2100 年不是闰年。
- 合并所有字段完全一致的记录；同名但字段不同的记录仍保留。
- 姓名、组别或日期缺失及无效日期会阻止此次更新，并提示原表行号，保留上一份有效数据。
- 出生日期在未来时提示核对，但仍按月日展示。
- 所有年份都基于当前名单，不代表历年实际在部人员。

## 公开内容与仓库

公开数据只有姓名、职能组、生日月日。`origin.xlsx`、Excel 临时文件及凭证文件均被 Git 忽略。姓名、生日数据本身仍属于公开网站可读取的内容。

建议 GitHub 仓库保持私有；Pages 网站可独立公开。登录 GitHub/Cloudflare 使用浏览器授权，不把访问令牌写入代码。

## 检查

```sh
node --test tests/calendar.test.mjs
python -m unittest discover -s tests
```

测试覆盖全范围日历、2100 年闰年边界、多选筛选、重复行及读取错误保留旧数据。

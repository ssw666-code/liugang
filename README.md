# liugang

## Smart Daily System 开发工程师交付

本仓库当前分支只包含开发工程师在前两周负责的成果。需求分析、系统设计、任务清单、测试报告和发布管理由对应角色另行提交。

第 1 周完成了环境验证、Python 3.12 最小工程骨架、`specs/` 目录和首次提交。第 2 周完成了 v1 业务代码、类图、关键序列图、接口工程可行性评审和开发自测。

## 开发实现

- GitHub Commits API 采集器。
- 飞书 Task v2 和 IM 消息采集器。
- 统一事件、规则化日报生成和稳定报告指纹。
- SQLite 事件、日报、关联记录和发送记录仓储。
- SMTP 邮件发送与本地 Outbox 演示实现。
- 主编排、单源故障隔离、发送幂等和 CLI。
- 3 名成员、3 类来源的脱敏 mock fixture。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts\verify_environment.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

无真实凭证演示：

```powershell
$env:SMART_DAILY_DATABASE_PATH = "data\demo.sqlite3"
$env:SMART_DAILY_RECIPIENTS = "team@example.com"
$env:PYTHONPATH = "src"
python -m smart_daily_system run --mock --date 2026-11-24
python -m smart_daily_system run --mock --date 2026-11-24
python -m smart_daily_system query --date 2026-11-24
```

第一次运行应显示 `Delivery: sent`，第二次相同输入应显示 `Delivery: skipped`。生成的邮件位于 `data/outbox/daily-report-2026-11-24.eml`。

## 开发工程师交付

```text
src/                     v1 业务实现
tests/                   开发单元与集成自测
fixtures/                脱敏演示数据
scripts/                 环境验证脚本
docs/week1/              环境验证、AI 日志、陷阱自查
docs/week2/              开发审查、静态检查、AI 日志、技能拆解
docs/uml/                类图、适配器类图、关键序列图
specs/README.md          规范目录占位，其他规范由对应角色提交
```

开发角色对应的课程要求见 `docs/week2/role-deliverables.md`。需求、设计、ADR、用例图、数据流图、ER 图、测试报告、Word 分析报告和 `v1-sdd` 发布标签不由本分支提交。

## CLI

```text
smart-daily doctor                  # 检查环境和凭证就绪状态
smart-daily init-db                 # 初始化 SQLite
smart-daily run --mock              # 使用 fixture 运行
smart-daily run                     # 使用真实平台配置运行
smart-daily run --no-send           # 只采集、生成和入库
smart-daily query --date YYYY-MM-DD # 查询已保存日报
```

真实模式配置见 `.env.example`。本地 `.env` 已被忽略，不能提交真实令牌、应用密钥或邮箱授权码。

## 质量门禁

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python -m compileall -q src tests scripts
```

当前结果：19 项测试通过，ruff 0 告警，格式和编译检查通过。

## 真实联调说明

GitHub 与飞书适配器已实现，但当前环境没有真实飞书应用和 SMTP 凭证，因此开发验收证据只覆盖 mock 闭环。凭证到位后仍需对飞书任务和消息的真实字段做 PoC；测试工程师可在此基础上补充正式集成测试记录。

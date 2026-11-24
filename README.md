# liugang

## Smart Daily System 第一周开发交付

本分支包含开发工程师第一周的 Python 3.12 最小工程、环境验证记录、`specs/` 目录占位、AI 使用日志和陷阱自查。需求、设计与仓库管理文件由对应角色另行提交。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts\verify_environment.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

工程结构：

```text
src/smart_daily_system/   Python 最小工程
tests/                    开发自测
scripts/                  环境验证
specs/README.md           规范目录占位
docs/week1/               第一周开发过程证据
```

提交前运行环境脚本、单元测试和静态检查，不得提交 `.env`、令牌、授权码或个人信息。

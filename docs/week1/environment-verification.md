# 第一周环境验证记录

| 项目 | 内容 |
| --- | --- |
| 验证日期 | 2026-11-11 |
| 时区 | Asia/Shanghai |
| 角色 | 开发工程师 |
| 验证环境 | Windows 11，项目目录 `D:\Codex_Code\SmartDailySystem` |
| 结论 | 本地 Python 开发与测试环境可用；`uv` 未安装；GitHub SSH（443 端口）认证、读取和 `liugang/main` 推送均通过 |

## 1. 验证命令

```powershell
python --version
python -c "import sqlite3; print(sqlite3.sqlite_version)"
git --version
sqlite3 --version
python scripts\verify_environment.py
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## 2. 实际结果

| 检查项 | 结果 | 实测值 | 判定 |
| --- | --- | --- | --- |
| Python | 已安装 | 3.12.4 | 通过 |
| Python 可执行文件 | 已定位 | `C:\Users\TangYi\anaconda3\python.exe` | 通过 |
| SQLite Python 模块 | 可导入 | 3.45.3 | 通过 |
| SQLite CLI | 已安装 | 3.45.3 | 通过 |
| Git | 已安装 | 2.20.1.windows.1 | 通过 |
| Git 用户信息 | 已配置 | 姓名和邮箱均已设置 | 通过 |
| `uv` | 未安装 | 未找到命令 | 警告，本次骨架无第三方依赖，不阻塞 |
| 工程目录 | 已创建 | `src/`、`specs/`、`tests/` | 通过 |
| Python 单元测试 | 6 项通过 | `python -m unittest discover -s tests -v` | 通过 |
| 可编辑安装 | 成功 | `pip install -e . --no-build-isolation` | 通过 |
| CLI 入口 | 成功 | `smart-daily version`、`smart-daily doctor` | 通过 |
| SQLite 初始化 | 成功 | `schema_version=1` | 通过 |
| GitHub SSH 远端 | 认证并读取成功 | `ssh://git@ssh.github.com:443/ssw666-code/-.git` | 通过 |
| GitHub HTTPS 直连 | 连接超时 | `github.com:443` 无响应 | 改用 SSH 443 |

说明：凭证检查只记录“是否配置”，不记录令牌、授权码或任何凭证值。

## 3. 最小工程启动验证

使用标准库和源码路径即可启动，不依赖网络：

```powershell
$env:PYTHONPATH = "src"
python -m smart_daily_system doctor
python -m smart_daily_system init-db --path data/verification.sqlite3
python -m unittest discover -s tests -v
```

验证完成后删除测试数据库：

```powershell
Remove-Item -LiteralPath "data\verification.sqlite3" -ErrorAction SilentlyContinue
```

`data/` 已被 `.gitignore` 排除，不进入仓库。

## 4. 处置与复验

1. 仓库 `origin` 使用 `ssh://git@ssh.github.com:443/ssw666-code/liugang.git`，已设置 `main` 跟踪并完成推送。
2. 如需使用 `uv`，安装后重新运行 `scripts/verify_environment.py`，该项应从 `WARN` 变为 `PASS`。
3. 后续加入第三方依赖时，必须提供可复现的锁文件和安装说明。

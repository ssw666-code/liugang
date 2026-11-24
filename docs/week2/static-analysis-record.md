# 第二周静态检查与安全记录

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| ruff 规则 | `python -m ruff check src tests scripts` | 0 告警 |
| ruff 格式 | `python -m ruff format --check src tests scripts` | 全部通过 |
| 字节码编译 | `python -m compileall -q src tests scripts` | 通过 |
| 单元/集成测试 | `python -m unittest discover -s tests -v` | 19 项通过 |
| PlantUML 语法 | `java -jar plantuml.jar -checkonly ...` | 3 张开发图通过 |
| 图表渲染 | `plantuml.jar -tsvg/-tpng` | 3 张 PNG/SVG 通过 |
| 秘密模式 | Git 暂存内容正则扫描 | 无匹配 |

## 安全自查

- SQL 全部使用参数绑定，不拼接外部输入。
- 令牌、应用密钥和邮箱密码使用 `repr=False`。
- `.env` 与运行数据库位于 `.gitignore` 排除目录。
- 发送记录只保存收件人哈希。
- 日志和错误信息只输出错误码与源名称。

# 第二周 AI 使用日志

| 日期 | 工具 | 用途与提示要点 | 产出与去向 | 人工核验方式 |
| --- | --- | --- | --- | --- |
| 2026-11-24 | Codex | 按课程指导书第 16-17 页核对第二周开发工程师任务 | `docs/week2/role-deliverables.md` | 对照 PDF 第 16-17 页 |
| 2026-11-24 | Codex | 从设计生成三个采集器、日报生成、SQLite、SMTP 与主编排 | `src/`、`fixtures/` | ruff、19 项测试、mock CLI 两次运行 |
| 2026-11-24 | Codex | 根据开发职责生成类图、适配器类图和关键序列图 | `docs/uml/` | 3 张图语法检查、PNG/SVG 渲染和目视检查 |
| 2026-11-24 | Codex | 拆解 Superpowers `requesting-code-review` 技能 | `docs/week2/skill-deconstruction.md` | 阅读 `SKILL.md` 与 `code-reviewer.md` |

## 说明

- AI 生成内容均通过自动化测试、静态检查或人工目视检查后才能进入提交。
- 未向 AI 提供真实令牌、应用密钥、邮箱授权码或个人敏感数据。
- 真实飞书 API 字段联调未执行，不能将 mock 结果表述为正式集成测试完成。

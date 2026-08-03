# Codex 三阶段可审计工作流

本项目提供一个可移植的 Analyze → Refine → Execute 工作流套件，重点解决两类
常见问题：规划模型持续钻入细节而不能退出，以及多个 subagents 同时写入导致文件
冲突、哈希漂移、重复构建和重复审计。

## 核心设计

- 只有显式 `$three-stage-complex-workflow` 或续接可核验的活动任务才激活本工作流；普通任务保留正常的读文件、生成文件、写文件和派生代理能力。
- 在活动三阶段任务内，`gpt-5.6-sol` 只承担 Analyze、Refine 和 Audit 的只读职责；
  `gpt-5.6-terra` 承担受批准范围约束的执行与集成。
- Analyze/Refine 使用 `StageExitContract`、有限证据轮次和 issue fingerprint
  终止无新增证据的反复检查。
- 并行读取可以存在；canonical 文件只允许 root integrator 顺序写入。
- writer 只写自己的 staging 目录；集成前核对 base revision、source hash、
  target pre-hash 和 manifest hash。
- seal 要求 quiescence 和两次稳定观察；纯 mtime 变化与内容变化分开处理。
- Audit receipt 同时绑定 revision、manifest、scope、cutoff、报告、findings、
  verdict 和 gates，避免审计结论脱离被审版本。

## 快速安装

```bash
git clone https://github.com/lianglunping/codex-three-stage-workflow.git
cd codex-three-stage-workflow
python3 scripts/audit_public_release.py .
python3 scripts/validate_all.py
python3 scripts/install.py --codex-home "${CODEX_HOME:-$HOME/.codex}"
python3 scripts/install.py --codex-home "${CODEX_HOME:-$HOME/.codex}" --apply
```

第一条安装命令只是 dry-run，不产生写入；只有 `--apply` 才会安装。安装器不会
修改 `config.toml` 或 `hooks.json`，也不建议合并全局写入 Guard。
`examples/hooks.strict.json` 仅供显式启动的专用严格三阶段会话人工审阅和选择。
已有目标会备份到 Codex home 内部的版本化 backup 目录。

若选择启用严格 Hook，在 Codex CLI 使用 `/hooks` 审阅并信任其当前哈希。Hook
变更后需要重新审阅。

## 从 v0.1.0 升级

如曾手工将旧的 `three_stage_write_guard.py` `PreToolUse` block 合并到用户
`hooks.json`，只删除该 block，保留其他所有 Hook。不要删除已安装脚本：它仍是
可选严格会话组件。必须完全重启 Codex 并开启新会话，才能重新加载 Hook 列表。

## 支持范围

- macOS 与 Linux；Python 3.9–3.13。
- 不声明原生 Windows 支持，因为控制面使用 `fcntl`。
- 默认公开 policy 只登记 Sol 与 Terra。增加其他模型前，必须先在实际 Codex
  版本中验证模型可用性和角色约束，再修改 policy 与回归用例。

详细说明见 [安装](installation.md)、[架构](architecture.md) 和
[安全边界](security-boundary.md)。

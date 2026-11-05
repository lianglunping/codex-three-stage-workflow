# Codex 三阶段工作流

按“分析问题 → 细化方案 → 执行方案”完成明确授权的任务，保留方案选择、实施批准、
范围和验收证据。公开包版本为 **0.2.0**，其中运行策略版本为 **2.1.0**。

## 使用方式

- `$three-stage-complex-workflow` 默认进入 `MANUAL`：每次回复只推进一个阶段，
  分析后等待选方案，细化后等待批准实施。
- 对具体任务明确提出“自动完成三阶段工作流”等要求时，使用 `BOUNDED_AUTO`，
  在记录的授权范围内自动选择、细化、执行及修复，仍须展示三个详细方案。
- 复杂、多文件、普通状态核查或维护工作流本身，不自动启用专用状态机。

分析恰好比较三个有实质差异的方案；细化逐文件说明变更、接口、验收及失败处理；
执行复用有效证据，验证实际交付物。新自动任务默认使用可续期修复周期，达到同一
问题三次或当期六次后，需有诊断、下一方法及进展或新证据，累计历史不能清零。
旧记录保留原固定预算语义。

新任务默认 Astra 分析/细化、Sol 执行，但必须核对实际运行时可用模型、身份、
任务能力及用户指定。模型不可用或委派未获授权时暂停，不静默替换。
子代理无固定模型白名单；自动推进不自动授权子代理、插件、外发、提交或推送。
root 是唯一正式文件集成者，最多一个活跃写入者。

## 安装与验证

```bash
git clone https://github.com/lianglunping/codex-three-stage-workflow.git
cd codex-three-stage-workflow
python3 scripts/audit_public_release.py .
python3 scripts/validate_all.py
python3 scripts/install.py --codex-home "${CODEX_HOME:-$HOME/.codex}"
python3 scripts/install.py --codex-home "${CODEX_HOME:-$HOME/.codex}" --apply
```

安装默认仅预览，实施时备份已有目标文件，不修改 AGENTS、config 或 hooks。
验证在临时 Codex home 中运行，使用仓库通用示例和合成测试，不读取个人任务。
仓库不包含本机配置、隐私、真实科研数据或运行记录。

旧版 Sol/Terra 写入钩子已退役；若曾手动启用，只移除该钩子配置条目并保留其他钩子。
升级不自动迁移活跃任务或收紧其原有授权。详见[安装与迁移](installation.md)、
[架构](architecture.md)及[安全边界](security-boundary.md)。

模型路由与状态校验属于结构检查，不能替代对批准真实性、科学结论和实际交付的核验。

# Project workflow example

## 复杂任务三阶段工作流

- 对复杂任务或显式 `$three-stage-complex-workflow`，依次使用
  `【分析问题】`、`【细化方案】`、`【执行方案】`；每次只进入一个阶段。
- 通过 `task_id`、`workflow_stage`、`approved_scope`、
  `approval_evidence` 和 `scope_fingerprint` 记录任务、批准与范围。
- 用户选择方案后才能 Refine；用户批准实施后才能 Execute。范围、输入、环境、
  风险或授权实质漂移时，退回受影响的规划阶段。
- 三阶段 Skill 只负责阶段、审批和范围门禁；专用 Skill 不得绕过三阶段批准边界。
- Analyze、Refine 和 Audit 保持只读；Execute 只在批准范围内写入。
- 多代理工作必须先核对当前唯一 deliverable、TODO、完成证据和 running
  assignments。允许并行读取，不允许重叠 canonical 写入；root 是唯一 integrator。
- 审计只接受绑定当前 sealed revision、manifest、scope 和 cutoff 的 receipt。

简单问答、只读状态核查、常规监控和小型明确修改不强制进入三阶段流程。

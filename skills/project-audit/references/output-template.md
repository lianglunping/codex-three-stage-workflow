# 审计报告输出模板

# 审计报告：[项目名称]

## 审计元信息

| 项目 | 内容 |
|---|---|
| 审计截点 | YYYY-MM-DD HH:MM TZ |
| 项目入口 | 路径、数据类型和版本 |
| 审计材料 | 文件清单或 manifest |
| 适用模块 | 模块编号 |
| 未审计或不适用范围 | 说明 |
| 审计模式 | 主审计 / 主审计 + 独立复核 |
| 独立复核触发依据 | 高风险 / 跨领域 / 结论敏感 / 发布前 / 用户要求 / 不适用 |
| Release 基线 | 版本、路径、checksum manifest |
| Canonical revision | revision_id |
| Revision manifest | manifest_sha256 |
| Scope fingerprint | scope_fingerprint |
| Audit receipt | receipt_id、valid_status、audit_cutoff |

## 审计范围与边界

- 可审计范围：
- 缺失材料：
- 明确不适用：
- 关键假设：
- delivery profile：

## 输入来源与不可变性

| Input ID | Path | Source/Version | Size | Checksum | Evidence Status | Note |
|---|---|---|---:|---|---|---|
| | | | | | VERIFIED/INFERRED/MISSING | |

## 基因组参考与坐标契约（如适用）

| Contract Item | Value | Evidence | Status |
|---|---|---|---|
| Species / assembly | | | |
| Reference FASTA checksum | | | |
| Annotation source/release | | | |
| Contig naming/alias | | | |
| Coordinate basis | | | |
| Strand/transcript rule | | | |
| REF/ALT and normalization | | | |
| Sample/material identity | | | |

## 数据流概览

    输入数据
      -> 步骤/工具/参数
      -> 中间集合及数量
      -> 语义 QA
      -> 冻结结果
      -> Release

对每个关键数量注明来源文件、字段、分母和复算方式。

## 语义验收结果

| Check | Expected | Observed | Evidence Path | Status |
|---|---|---|---|---|
| | | | | PASS/CONCERN/FAIL/NOT_VERIFIED |

## 跨格式与 Release 一致性

| Surface | Canonical Source | Compared Artifact | Equivalence Rule | Status | Evidence |
|---|---|---|---|---|---|
| TSV/XLSX | | | keys/columns/rows/values | | |
| Figure/source table | | | named linkage | | |
| README/results | | | numbers/versions | | |
| Release/manifest | | | whitelist/checksum | | |

## Revision 与并发协调（如适用）

| Item | Expected | Observed | Evidence | Status |
|---|---|---|---|---|
| Canonical integrator | root only | | assignment registry | |
| Active write scopes | disjoint staging only | | assignment registry | |
| Quiescence | all assignments/jobs terminal | | registries | |
| Stable observations | two identical manifests | | snapshots | |
| Audit binding | revision + manifest + scope + cutoff | | receipt | |
| Post-seal drift | classified and handled | | invalidation/evidence | |

## 问题清单

### Critical

#### C1. [问题标题]

- **位置**：文件、行号、sheet、字段或日志时间。
- **问题类别**：输入完整性 / 坐标契约 / 数据 / 代码 / 方法 /
  语义 QA / 跨格式一致性 / 文档 / 结论 / 复现性 / Release。
- **证据状态**：VERIFIED / INFERRED / MISSING。
- **问题描述**：
- **证据依据**：
- **影响**：对科学结论、数据完整性、复现或发布的影响。
- **严重度理由**：
- **修正建议**：
- **复核方式**：命令、脚本、表格或人工检查。
- **发现来源**：主审计 / 独立复核 / 交叉验证。

### Major

#### M1. [同上格式]

### Minor

#### m1. [同上格式]

### Suggestion

#### S1. [同上格式]

## 审计维度状态

| 维度 | 状态 | 主要证据或问题 |
|---|---|---|
| 输入完整性与不可变性 | PASS/CONCERN/FAIL/NA/NOT_VERIFIED | |
| 数据可追溯性 | | |
| 基因组坐标完整性（如适用） | | |
| 代码与流程可靠性 | | |
| 方法学合理性 | | |
| 语义结果有效性 | | |
| 跨格式一致性 | | |
| 结论强度 | | |
| 可复现性 | | |
| Release/version 完整性 | | |
| Revision seal / audit receipt（如适用） | | |

## 独立复核与分歧裁定（如执行）

### 一致发现

- finding：

### 独立发现

- finding：

### 分歧与裁定

| 问题 | 主审计判断 | 独立复核判断 | 最终裁定 | 证据依据 |
|---|---|---|---|---|
| | | | | |

## 结论分层

### 直接支持的结论

- 结论 — 证据路径、字段和复核方式。

### 合理推断

- 推断 — 依据 — 证据强度 — 仍需验证。

### 证据不足或表述过强

- 原表述 — 风险 — 建议改写 — 缺失证据。

## 验收门禁

| Gate | Status | Evidence |
|---|---|---|
| 输入完整性/不可变性 | PASS/FAIL/NA/NOT_VERIFIED | |
| 核心结果可追溯 | | |
| 语义 QA | | |
| 坐标契约（如适用） | | |
| TSV/XLSX 等价（如适用） | | |
| 方法适用性与结论强度 | | |
| 可复现性 | | |
| Release/version/manifest | | |
| Revision seal / audit receipt（如适用） | | |

## 总体判定

**Ready / Need Minor Revision / Need Major Revision / Not Ready**

- 已通过门禁：
- 不适用门禁及理由：
- 未验证项及影响：
- 未关闭 Critical：
- 影响适用门禁的未关闭 Major：
- 非阻塞限制：
- 建议修订优先级：
- 当前 receipt 是否仍绑定 current canonical revision：

只有全部适用关键门禁通过、无未关闭 Critical，且无影响适用门禁的
未关闭 Major 时，才判 Ready。

# 审计检查清单

## A. Scope and Evidence Inventory

- [ ] 确认项目入口、审计截点和用户要求的交付/发布范围。
- [ ] 列出可用材料、缺失材料和明确不适用的材料。
- [ ] 选择适用审计模块并记录风险等级。
- [ ] 定义 delivery profile，不将 fastq/VCF/GVCF 视为唯一入口。
- [ ] 建立输入 manifest：路径、大小、来源、版本和 checksum。
- [ ] 记录符号链接实际目标、原始输入边界和不可变性证据。
- [ ] 决定是否需要独立复核并记录理由。
- [ ] 多代理或可变工作区已记录 canonical revision、manifest、scope fingerprint
      和 audit cutoff。

## B. Recon and Contracts

- [ ] 识别入口脚本、配置、环境、结果、文档、release 和归档。
- [ ] 绘制数据流以及样本、位点、记录数的阶段变化。
- [ ] 标出关键数字、图表和结论的生成来源。
- [ ] 记录手工步骤、临时脚本、孤儿文件和未知输入。
- [ ] 若适用，建立 assembly、annotation、contig、coordinate、strand、
      transcript 和 REF/ALT 契约。
- [ ] 核对 FASTA/GFF/VCF/索引/数据库版本及 checksum。
- [ ] 对未知项标记 MISSING，不用默认值补齐。

## C. Module Execution

### 输入完整性与不可变性

- [ ] 原始输入与中间/最终输出已分离。
- [ ] 输入 checksum 在运行或修订前后未发生未解释变化。
- [ ] 仅有文件存在或 mtime 时未将其写成强不可变证据。

### 数据与数量追溯

- [ ] 样本、位点、记录和分类总数可由命名结果复算。
- [ ] 主键唯一性和 join cardinality 已检查。
- [ ] 分母、过滤集合和父子集合定义一致。
- [ ] 图表可追溯到源表或明确计算。
- [ ] 重复计数、漏计、选择性汇报和断链已检查。

### 基因组坐标契约

- [ ] assembly 与 annotation 匹配。
- [ ] contig 名称、顺序、长度和别名映射一致。
- [ ] BED/VCF/GFF 坐标基准和端点转换明确。
- [ ] strand、reverse-complement 和 transcript 选择规则明确。
- [ ] VCF REF 与参考序列匹配。
- [ ] normalization、multiallelic、symbolic allele、END/SVLEN 规则明确。
- [ ] 样本、材料、世代、组织、地点、时间和批次标识一致。

### 代码与流程

- [ ] 输入 schema、参数、路径和空输入验证存在。
- [ ] 阈值比较符、off-by-one 和缺失值处理正确。
- [ ] 命令失败可传播，部分输出不会被误判为完成。
- [ ] 并行、随机性和随机种子已记录。
- [ ] 路径已参数化，跨主机/环境假设已核对。
- [ ] 输出 schema、列定义和命名与实现一致。

### 语义验收与跨产物一致性

- [ ] 关键产物 schema、主键、记录数和允许范围通过。
- [ ] README、方法、表格、图、报告和 release 中数字一致。
- [ ] TSV 与 XLSX 的 sheet、列、主键、记录数和内容已比较。
- [ ] 空值、日期、公式值、浮点容差和排序规范明确。
- [ ] Excel 截断、隐藏 sheet、长 ID 和类型转换已检查。
- [ ] 文件存在或 exit code 0 未被单独当作结果通过。

### 方法与结论

- [ ] 工具、参数、参考资源和阈值适用且有依据。
- [ ] 统计功效、混杂、多重检验和独立验证已考虑。
- [ ] 直接证据、合理推断和证据不足已区分。
- [ ] 相关/共分离未被无依据提升为因果。
- [ ] 检出、诱发、遗传、机制和育种价值未被自动等同。
- [ ] 负结果、限制、反例和隐含假设未被省略。

### 可复现性

- [ ] 精确入口、命令、参数、环境、版本和输入输出映射存在。
- [ ] 人工/临时步骤有记录。
- [ ] 随机过程与平台差异有控制或说明。
- [ ] 重跑验收层级为 bitwise、结构等价或语义等价之一。
- [ ] 最小复现路径或完整 provenance 可用。

### Release 与版本面

- [ ] active 与 superseded 版本明确。
- [ ] 文件名、表头、图例、README、manifest 和包内版本一致。
- [ ] release 白名单正确，无旧版、临时文件或内部敏感内容。
- [ ] checksum manifest 可验证。
- [ ] TSV/XLSX/图/报告来自同一冻结结果。
- [ ] 解压后的交付可独立理解和复核。

### 多代理 revision 与审计绑定

- [ ] assignment registry 中角色、base revision、读写域和状态完整。
- [ ] root 是唯一 canonical integrator，writer 的 staging 路径互斥。
- [ ] seal 前所有 assignment/job 已 terminal，两个 manifest 观察一致。
- [ ] audit receipt 绑定 revision、manifest SHA256、scope fingerprint 和 cutoff。
- [ ] auditor/独立复核只读且检查相同 sealed revision。
- [ ] post-seal drift 已分类，semantic/late-write 已使旧 receipt 失效。
- [ ] 未因 mtime-only 或 out-of-scope 变化机械触发全量重跑。

## D. Independent Review

仅在高风险、跨领域、结论敏感、正式发布前或用户要求时启用。

- [ ] 独立复核者收到相同范围和原始材料。
- [ ] 复核未依赖主审计的预设结论。
- [ ] 一致发现、独有发现和分歧均已记录。
- [ ] 分歧按证据裁定，而不是按模型身份或票数。
- [ ] 独立复核与主审计绑定相同 revision、manifest、scope 和 cutoff。

## E. Synthesis and Acceptance

- [ ] 每个 finding 有位置、证据状态、影响、严重度和复核方式。
- [ ] 相同根因已合并，未重复计数。
- [ ] 已确认事实、推断、假设和缺口分别表达。
- [ ] 核心数字已复算，或明确标记 NOT_VERIFIED。
- [ ] 适用的输入、坐标、语义 QA、跨格式、方法与结论强度、可复现性和
      release 门禁已填写。
- [ ] revision-bound 审计适用时，receipt 已现场复验为 Valid。
- [ ] 任一未关闭 Critical 存在时未判 Ready。
- [ ] 影响任一适用门禁的未关闭 Major 存在时未判 Ready。
- [ ] NOT_APPLICABLE 项有理由，MISSING 项说明对结论的影响。

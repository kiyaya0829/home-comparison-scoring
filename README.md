# Home Comparison Scoring — Smooth v2

独立的 Python 评分模块，供 SC2006 Home Comparison System 迁移使用。无第三方运行依赖，不读取凭据、不调用 API、不修改输入。原型参数仍需团队验证；分数不是满意概率。

## 公式与参数

- 每周负担 B = 单程分钟 × 每周次数 × trip-leg factor。此模块接收已经计算好的 weekly_minutes，不再次乘频率。
- 交通 T = 100 × τ / (τ + B)，默认 τ = 300 分钟。
- 距离 D = 100 × δ / (δ + d)，默认 δ = 500 米。
- 数量 N = 100 × n / (ν + n)，默认 ν = 3，n 为 1 km 内去重设施数。
- 设施 A = αD + (1−α)N，默认 α = 0.5。
- 综合 S = Σ(w × criterion score) / Σw；High / Medium / Low = 3 / 2 / 1。

τ、δ、ν 是对应单项获得 50 分的输入值，不是最大允许值。平滑函数避免超过阈值后一律为零，数量收益递减。默认所有设施类别共用参数；本版未实现分类别校准。

## 数据与结果规则

只在所有候选均有有效证据的指标上计算总分。缺失数据为 unavailable，不能填零。最近距离未知时，整个设施指标不可用；查询得到真实零数量时则保留零数量。负数、非有限数和非整数设施数被拒绝。

coverage = 共同有效指标数 / 选定指标数 × 100%，单独显示，不乘入总分。

Complete：全部指标可比；Partial：部分指标可比；Inconclusive：没有共同指标。只有 Complete 返回 highest_fit_candidates，它仅表示该提案下的最高匹配候选，不是已验证推荐。原有 warning / decision 继续标注实验性质。

总分保留两位小数后排序，相同显示分数并列，名次为 1、1、3；并列保留输入顺序。内部单项与贡献计算保留精度。Python round 使用 ties-to-even。

contributions 是每项加权贡献。pairwise.contribution_differences 给出两房屋逐项贡献差；差值之和等于未舍入总分差。不要将这些差值当成统计置信度。输出记录 version 和 parameters；复现必须保存二者以及输入和证据快照。

## 使用

```python
from scoring import score, ExperimentalPolicy

criteria = [{"id": "work", "label": "Work", "importance": "High"}]
rows = [{"postal_code": "Example A", "metrics": {
    "work": {"type": "travel", "available": True, "weekly_minutes": 300}
}}]
result = score(rows, criteria)  # overall = 50.0
# 参数实验：
result = score(rows, criteria, policy=ExperimentalPolicy(travel_half=400))
```

运行测试：`python -m unittest discover -s tests -v`。

迁移步骤见 [docs/MIGRATION.md](docs/MIGRATION.md)。没有复制原项目数据、环境文件或凭据，也没有更改原项目。

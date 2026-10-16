# 迁移到 SC2006_Prototype

1. 新建功能分支，保留原评分文件以便回滚。
2. 将本仓库 scoring.py 复制为 backend/closeforwhom/scoring.py。
3. scoring_preview.py 的现有导入可保留：VERSION、WEIGHTS、clamp、criterion_score、score 仍存在。score 的 scorer / policy 注入接口保留。
4. 前端如需展示新字段，应接入 status、coverage、rank、contributions、pairwise 和 highest_fit_candidates；本仓库不包含这些 UI 改动。旧响应字段仍保留。
5. 测试迁移时将 `from scoring import ...` 改为 `from closeforwhom.scoring import ...`。原 test_default_policy_preserves_existing_arithmetic 预期需要改成新版公式；60 / 180 分钟对应 83.33 / 62.50，不能继续预期 90 / 70。
6. 检查项目其余测试、快照、公式说明和界面中旧的 600 / 2000 / 10 阈值文案。运行完整后端测试和涉及评分的前端流程测试后再合并。

只改重要性时，调用方应传入现有有效 evidence snapshot 和新的 criteria，不调用 provider。模块自身不做数据获取；本包离线测试验证纯计算和输入不变，但不代表原项目端到端集成已经验证。

输入保留原项目结构：rows 中包含 postal_code、metrics；可选 candidate_id 和 label 用于区分相同邮编的房源。criterion id 必须唯一，importance 使用 High / Medium / Low。上游仍负责候选数量、单位、来源有效性和快照新鲜度验证。

分数规则仍为提案。团队应使用多个真实结构、合成数值的算例校准参数，并进行排名敏感性验证。尚未实现分类别参数、自动敏感性分析或推断推荐可信度。

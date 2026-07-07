from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

APP = Path(r"C:\Users\Administrator\Documents\exam\index.html")
REPORT = Path(r"C:\Users\Administrator\Documents\exam\分类优化报告.json")

MANUAL_OVERRIDES = {
    "q0476": "BA",
    "q0710": "digital-transformation",
}

BUSINESS_HINTS = [
    ("digital-transformation", ["数智化", "数字化转型", "转型", "一汽", "双100", "1174", "业务在线", "数字孪生", "数智运营", "自主可控", "组织变革", "业务变革", "最后一公里"]),
    ("data-governance", ["数据治理", "指标治理", "指标", "原子指标", "派生指标", "复合指标", "统计口径", "口径", "度量", "数据项", "数据源", "数据标准", "元数据", "数据质量", "数据仓库", "主题域", "主数据", "事务数据", "第二范式", "第三范式", "数据架构", "探源", "认证数据源"]),
    ("AA", ["应用架构", "应用组件", "应用服务", "组件契约", "应用上下文", "应用交互", "时序图", "应用资产", "应用域", "应用系统", "应用路线图", "接口", "API", "微服务", "服务网格", "容器", "云原生", "CRUD", "应用-数据", "应用-业务", "技术栈", "系统边界", "组件", "契约"]),
    ("product-design", ["产品设计", "PRD", "用户故事", "史诗", "故事线", "用户旅程", "用户画像", "原型", "MVP", "KANO", "MoSCoW", "SMART", "希克", "格式塔", "奥卡姆", "需求清单", "需求详述", "竞品", "用户体验", "可用性", "TAM模型"]),
    ("BA", ["业务架构", "业务单元", "业务活动", "业务流程", "能力流程", "业务组件", "业务能力", "价值流", "业务场景", "场景因子", "灯塔指标", "利益相关者", "价值主张", "业务对象", "流程分类", "企业流程", "TAM模型", "业务规则", "关键触点"]),
    ("IA", ["信息架构", "概念模型", "逻辑模型", "物理模型", "实体关系", "逻辑实体", "逻辑数据", "主标识符", "属性定义", "编码规则", "数据分布", "信息链", "信息链路", "数据模型", "六阶十八步", "业务术语"]),
]

def find_questions_bounds(html: str) -> tuple[int, int]:
    marker = "    const questions = "
    start = html.find(marker)
    if start < 0:
        raise RuntimeError("未找到 const questions")
    array_start = html.find("[", start)
    depth = 0
    in_string = False
    escape = False
    for idx in range(array_start, len(html)):
        ch = html[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    semi = html.find(";", idx)
                    return start, semi + 1
    raise RuntimeError("questions 数组未闭合")

def load_questions(html: str) -> list[dict]:
    start, end = find_questions_bounds(html)
    raw = html[start:end].split("=", 1)[1].rsplit(";", 1)[0].strip()
    return json.loads(raw)

def dump_questions(html: str, questions: list[dict]) -> str:
    start, end = find_questions_bounds(html)
    js = "    const questions = " + json.dumps(questions, ensure_ascii=False, indent=6) + ";"
    js = js.replace("\n", "\n    ", 1)
    return html[:start] + js + html[end:]

def classify(question: dict) -> tuple[str, dict[str, int]]:
    text = f"{question.get('question', '')} {' '.join(question.get('options', []))} {question.get('analysis', '')}"
    scores = {}
    for business, hints in BUSINESS_HINTS:
        score = 0
        for hint in hints:
            if hint.lower() in text.lower():
                score += 10 + min(len(hint), 8)
        scores[business] = score
    ia_boost_hints = ["信息架构", "概念模型", "逻辑模型", "物理模型", "实体关系", "逻辑实体", "逻辑数据", "主标识符", "属性定义", "编码规则", "数据分布", "信息链", "数据模型", "六阶十八步", "业务术语"]
    for hint in ia_boost_hints:
        if hint in text:
            scores["IA"] += 18 + min(len(hint), 8)
    if re.search(r"(?<![A-Za-z])IA(?![A-Za-z])", text):
        scores["IA"] += 35
    if "指标" in text or "数据治理" in text or "指标治理" in text:
        scores["data-governance"] += 18
    if "应用架构" in text or "应用组件" in text or "应用服务" in text:
        scores["AA"] += 18
    if "业务架构" in text or "业务流程" in text or "业务能力" in text:
        scores["BA"] += 18
    if "产品设计" in text or "用户故事" in text or "PRD" in text:
        scores["product-design"] += 18
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return question.get("business") or "BA", scores
    return best, scores

def patch_css(html: str) -> str:
    html = html.replace("""    .quiz-wrap {
      display: flex;
      flex-direction: column;
      gap: 12px;
      flex: 1;
      padding-bottom: 8px;
    }""", """    .quiz-wrap {
      display: flex;
      flex-direction: column;
      gap: 12px;
      flex: 1;
      padding-bottom: 112px;
    }""")
    html = html.replace("""    .option {
      display: grid;
      grid-template-columns: 32px 1fr;
      gap: 10px;
      align-items: center;
      width: 100%;
      border: 1px solid #d7ded9;
      border-radius: 8px;
      background: #fff;
      padding: 12px;
      text-align: left;
      line-height: 1.5;
      color: var(--text);
    }

    .option.selected {
      border-color: var(--blue);
      background: var(--blue-soft);
    }""", """    .option {
      display: grid;
      grid-template-columns: 32px 1fr;
      gap: 10px;
      align-items: center;
      width: 100%;
      border: 1px solid #d7ded9;
      border-radius: 8px;
      background: #fff;
      padding: 12px;
      text-align: left;
      line-height: 1.5;
      color: var(--text);
      position: relative;
    }

    .option.selected {
      border-color: var(--blue);
      background: var(--blue-soft);
      box-shadow: 0 0 0 2px rgba(47, 95, 158, 0.18);
      font-weight: 720;
    }

    .option.selected::after {
      content: "已选";
      position: absolute;
      top: 8px;
      right: 10px;
      border-radius: 999px;
      background: var(--blue);
      color: #fff;
      padding: 2px 7px;
      font-size: 12px;
      font-weight: 760;
    }""")
    html = html.replace("""    .quiz-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: auto;
    }""", """    .multi-tip {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 14px;
      border-radius: 8px;
      background: var(--gold-soft);
      color: #6f4a12;
      border: 1px solid #efcf92;
      padding: 10px 12px;
      font-size: 14px;
      font-weight: 760;
      line-height: 1.45;
    }

    .multi-tip::before {
      content: "多选";
      flex: 0 0 auto;
      border-radius: 999px;
      background: var(--gold);
      color: #fff;
      padding: 2px 8px;
      font-size: 12px;
    }

    .quiz-actions {
      position: fixed;
      left: 50%;
      bottom: 0;
      z-index: 20;
      width: min(100%, 430px);
      transform: translateX(-50%);
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin: 0;
      padding: 10px 16px calc(10px + env(safe-area-inset-bottom));
      background: rgba(246, 247, 244, 0.96);
      border-top: 1px solid var(--line);
      box-shadow: 0 -10px 26px rgba(28, 45, 40, 0.12);
      backdrop-filter: blur(12px);
    }""")
    return html

def patch_render(html: str) -> str:
    html = html.replace("""      const confirmButton = question.type === "multiple"
        ? `<button class="secondary full-row" data-action="confirm" ${revealed ? "disabled" : ""}>确认答案</button>`
        : "";
      const otherAnswer = question.type === "other"
        ? `<div class="answer-box"><strong>参考答案</strong><p>${escapeHtml(question.answerText || "")}</p><p>${escapeHtml(question.analysis || "")}</p></div>`
        : "";""", """      const confirmButton = question.type === "multiple"
        ? `<button class="primary full-row" data-action="confirm" ${revealed ? "disabled" : ""}>确认多选答案</button>`
        : "";
      const multiTip = question.type === "multiple" && !revealed
        ? `<div class="multi-tip">可选择多个答案，选完后点击底部“确认多选答案”。</div>`
        : "";
      const otherAnswer = question.type === "other"
        ? `<div class="answer-box"><strong>参考答案</strong><p>${escapeHtml(question.answerText || "")}</p><p>${escapeHtml(question.analysis || "")}</p></div>`
        : "";""")
    html = html.replace("""          <p class="question">${escapeHtml(question.question)}</p>
          ${question.type !== "other" ? renderOptions(question, record, revealed) : otherAnswer}""", """          <p class="question">${escapeHtml(question.question)}</p>
          ${multiTip}
          ${question.type !== "other" ? renderOptions(question, record, revealed) : otherAnswer}""")
    return html

def main() -> None:
    html = APP.read_text(encoding="utf-8-sig")
    questions = load_questions(html)
    changes = []
    for question in questions:
        old = question.get("business")
        new, scores = classify(question)
        new = MANUAL_OVERRIDES.get(question.get("id"), new)
        if new != old:
            question["business"] = new
            changes.append({"id": question.get("id"), "question": question.get("question"), "from": old, "to": new, "scores": scores})
    html = dump_questions(html, questions)
    html = patch_css(html)
    html = patch_render(html)
    APP.write_text(html, encoding="utf-8")
    report = {"question_count": len(questions), "changed_count": len(changes), "business_counts": dict(Counter(q.get("business") for q in questions)), "changes_sample": changes[:120]}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()





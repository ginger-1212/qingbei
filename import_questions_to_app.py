from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path


SOURCE_DIR = Path(r"C:\Users\Administrator\Desktop\知识点\02试题整理\整理好的")
APP_FILE = Path(r"C:\Users\Administrator\Documents\exam\index.html")
OTHER_OUT = Path(r"C:\Users\Administrator\Desktop\知识点\02试题整理\整理好的\其他题_未导入应用.txt")
WORK_OTHER_OUT = Path(r"C:\Users\Administrator\Documents\exam\其他题_未导入应用.txt")
REPORT = Path(r"C:\Users\Administrator\Documents\exam\题库导入报告.json")

TYPE_MAP = {
    "单选": "single",
    "单选题": "single",
    "单项选择题": "single",
    "多选": "multiple",
    "多选题": "multiple",
    "多项选择题": "multiple",
    "案例": "other",
    "案例题": "other",
    "其他": "other",
    "其他题": "other",
}

BUSINESS_KEYS = {
    "BA": "BA",
    "IA": "IA",
    "AA": "AA",
    "数据治理": "data-governance",
    "指标治理": "data-governance",
    "产品设计": "product-design",
    "PD": "product-design",
    "数字化转型": "digital-transformation",
    "数智化转型": "digital-transformation",
    "PMP": "PMP",
    "NPDP": "NPDP",
    "云原生": "cloud-native",
    "产品思维": "product-thinking",
}


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def split_blocks(text: str) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    pattern = re.compile(r"(?m)^\s*(?:\d+\s*[.、]\s*)?【(?:单选题?|单项选择题|多选题?|多项选择题|案例题?|其他题?)】")
    matches = list(pattern.finditer(text))
    blocks: list[str] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[match.start():end].strip()
        if block:
            blocks.append(block)
    return blocks


def detect_type(head: str) -> str:
    match = re.search(r"【([^】]+)】", head)
    return TYPE_MAP.get(match.group(1), "other") if match else "other"


def file_business(path: Path) -> str | None:
    name = path.stem
    if name.startswith("BA"):
        return "BA"
    if name.startswith("IA"):
        return "IA"
    if name.startswith("AA"):
        return "AA"
    if "集团公司数智化转型" in name:
        return "digital-transformation"
    return None


def infer_business(path: Path, head: str, body: str) -> str:
    combined = f"{path.stem}\n{head}\n{body}"
    for label, key in BUSINESS_KEYS.items():
        if label in combined:
            return key
    if any(k in combined for k in ("指标", "口径", "原子指标", "派生指标", "数据项", "数据源", "数据治理")):
        return "data-governance"
    if any(k in combined for k in ("应用架构", "应用组件", "组件契约", "应用服务", "应用上下文", "应用交互", "微服务", "接口", "应用资产")):
        return "AA"
    if any(k in combined for k in ("产品设计", "PRD", "用户故事", "史诗", "故事线", "MVP", "KANO", "用户旅程", "原型", "希克定律", "格式塔")):
        return "product-design"
    if any(k in combined for k in ("数智化", "数字化", "双100", "1174", "业务在线", "数字孪生", "转型")):
        return "digital-transformation"
    if any(k in combined for k in ("云原生", "容器", "Kubernetes", "DevOps", "服务网格")):
        return "cloud-native"
    return file_business(path) or "product-thinking"


def clean_head(head: str) -> str:
    head = re.sub(r"^\s*\d+\s*[.、]\s*", "", head).strip()
    head = re.sub(r"【[^】]+】", "", head).strip()
    return head


def parse_block(path: Path, block: str) -> dict | None:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return None
    qtype = detect_type(lines[0])
    question_parts = [clean_head(lines[0])]
    options: dict[str, str] = {}
    answer = ""
    analysis_parts: list[str] = []
    current_option: str | None = None
    mode = "question"

    for line in lines[1:]:
        answer_match = re.match(r"^答案[:：]\s*(.+?)\s*$", line)
        analysis_match = re.match(r"^(?:解析|简析|参考解析)[:：]\s*(.*)$", line)
        option_match = re.match(r"^([A-H])[.、]\s*(.+?)\s*$", line)
        if answer_match:
            answer = answer_match.group(1).strip()
            current_option = None
            mode = "answer"
        elif analysis_match:
            text = analysis_match.group(1).strip()
            if text:
                analysis_parts.append(text)
            current_option = None
            mode = "analysis"
        elif option_match and qtype in {"single", "multiple"}:
            current_option = option_match.group(1)
            options[current_option] = option_match.group(2).strip()
            mode = "options"
        elif mode == "analysis":
            analysis_parts.append(line)
        elif current_option:
            options[current_option] = f"{options[current_option]} {line}".strip()
        elif not line.startswith(("一、", "二、", "三、")):
            question_parts.append(line)

    question = " ".join(part for part in question_parts if part).strip()
    option_letters = sorted(options.keys())
    answer_letters = re.findall(r"[A-H]", answer.upper())
    if qtype in {"single", "multiple"} and (not question or not option_letters or not answer_letters):
        qtype = "other"

    business = infer_business(path, lines[0], block)
    if qtype == "other":
        return {
            "type": "other",
            "business": business,
            "question": question or clean_head(lines[0]),
            "answerText": answer,
            "analysis": " ".join(analysis_parts).strip(),
            "source": path.name,
            "raw": block.strip(),
        }

    return {
        "type": qtype,
        "business": business,
        "question": question,
        "options": [options[key] for key in option_letters],
        "answer": answer_letters,
        "analysis": " ".join(analysis_parts).strip() or f"答案为{''.join(answer_letters)}。",
        "source": path.name,
    }


def question_key(item: dict) -> str:
    return re.sub(r"\W+", "", item.get("question", "")).lower()


def build_other_txt(items: list[dict]) -> str:
    parts = []
    for i, item in enumerate(items, 1):
        parts.append(
            "\n".join(
                [
                    f"{i}. 【其他】{item['question']}",
                    f"   业务分类：{item['business']}",
                    f"   来源：{item['source']}",
                    f"   答案：{item.get('answerText', '')}",
                    f"   解析：{item.get('analysis', '')}",
                    "   原文：",
                    item.get("raw", ""),
                ]
            )
        )
    return "\n\n".join(parts).strip() + ("\n" if parts else "")


def replace_questions(app_text: str, questions: list[dict]) -> str:
    payload_items = []
    for i, item in enumerate(questions, 1):
        payload = {
            "id": f"q{i:04d}",
            "type": item["type"],
            "business": item["business"],
            "question": item["question"],
            "options": item["options"],
            "answer": item["answer"],
            "analysis": item["analysis"],
        }
        payload_items.append(payload)
    js = "    const questions = " + json.dumps(payload_items, ensure_ascii=False, indent=6) + ";"
    js = js.replace("\n", "\n    ", 1)
    pattern = re.compile(r"    const questions = \[.*?\n    \];", re.S)
    new_text, count = pattern.subn(js, app_text, count=1)
    if count != 1:
        raise RuntimeError("没有找到 index.html 中的 const questions 数组")
    return new_text


def main() -> None:
    imported: list[dict] = []
    other: list[dict] = []
    seen: set[str] = set()
    duplicates = 0

    for path in sorted(SOURCE_DIR.glob("*.txt")):
        if path.name.startswith("其他题_"):
            continue
        for block in split_blocks(read_text(path)):
            item = parse_block(path, block)
            if not item:
                continue
            key = question_key(item)
            if key and key in seen:
                duplicates += 1
                continue
            seen.add(key)
            if item["type"] in {"single", "multiple"}:
                imported.append(item)
            else:
                other.append(item)

    other_txt = build_other_txt(other)
    OTHER_OUT.write_text(other_txt, encoding="utf-8")
    WORK_OTHER_OUT.write_text(other_txt, encoding="utf-8")

    backup = APP_FILE.with_name("index_导入题库前备份.html")
    if not backup.exists():
        shutil.copy2(APP_FILE, backup)
    app_text = read_text(APP_FILE)
    APP_FILE.write_text(replace_questions(app_text, imported), encoding="utf-8")

    report = {
        "source_dir": str(SOURCE_DIR),
        "app_file": str(APP_FILE),
        "backup": str(backup),
        "other_out": str(OTHER_OUT),
        "imported_count": len(imported),
        "other_count": len(other),
        "duplicates_skipped": duplicates,
        "by_type": dict(Counter(item["type"] for item in imported)),
        "by_business": dict(Counter(item["business"] for item in imported)),
        "other_by_business": dict(Counter(item["business"] for item in other)),
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

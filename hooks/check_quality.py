#!/usr/bin/env python3
"""5-dimension quality scoring for knowledge entry JSON files."""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""

    name: str
    score: float
    max_score: float
    reason: str = ""


@dataclass
class QualityReport:
    """Quality report for a single knowledge entry."""

    file_path: str
    total_score: float
    dimensions: list[DimensionScore] = field(default_factory=list)
    grade: str = ""

    def __post_init__(self) -> None:
        if self.total_score >= 80:
            self.grade = "A"
        elif self.total_score >= 60:
            self.grade = "B"
        else:
            self.grade = "C"


BUZZWORDS_CN: frozenset[str] = frozenset({
    "赋能", "抓手", "闭环", "打通", "全链路", "底层逻辑",
    "颗粒度", "对齐", "拉通", "沉淀", "强大的", "革命性的",
})

BUZZWORDS_EN: frozenset[str] = frozenset({
    "groundbreaking", "revolutionary", "game-changing", "cutting-edge",
    "state-of-the-art", "disruptive", "paradigm-shift", "next-generation",
    "world-class", "best-in-class",
})

STANDARD_TAGS: frozenset[str] = frozenset({
    "AI", "LLM", "Agent", "NLP", "计算机视觉", "强化学习", "深度学习",
    "机器学习", "大语言模型", "多模态", "推理", "RAG", "对话系统",
    "知识图谱", "语音识别", "图像生成", "文本生成", "代码生成",
    "开源工具", "框架", "数据集", "评测基准", "部署", "训练",
    "微调", "对齐", "安全", "隐私", "多智能体",
    "工具使用", "规划", "记忆", "检索", "搜索引擎", "编程助手",
    "研究工具", "NLP研究工具", "模型压缩", "量化", "蒸馏",
    "推理加速", "边缘计算", "RLM", "递归语言模型",
    "沙盒环境", "交易", "金融", "视频生成",
    "短视频", "产品管理", "技能市场", "安全扫描",
    "AIGC", "内容创作", "自动化", "Claude", "开发工具", "语音交互",
    "VSCode", "模型评估", "Agent开发", "向量数据库", "提示工程",
})


def detect_buzzwords(text: str) -> list[str]:
    """Return all buzzwords found in text."""
    found: list[str] = []
    for bw in BUZZWORDS_CN:
        if bw in text:
            found.append(bw)
    lower = text.lower()
    for bw in BUZZWORDS_EN:
        if bw in lower:
            found.append(bw)
    return found


def evaluate_summary(entry: dict[str, Any]) -> DimensionScore:
    """Score summary quality (max 25)."""
    summary = entry.get("summary", "")
    if not isinstance(summary, str):
        return DimensionScore("摘要质量", 0.0, 25, "缺少 summary 字段")

    length = len(summary)
    score = 0.0
    reasons: list[str] = []

    if length >= 50:
        score = 20.0
        reasons.append(f"长度{length}字≥50")
    elif length >= 20:
        score = 15.0
        reasons.append(f"长度{length}字≥20")
    else:
        score = 10.0
        reasons.append(f"长度{length}字<20")

    tech_keywords = {
        "AI", "LLM", "模型", "智能", "推理", "训练", "学习",
        "深度", "神经", "算法", "数据", "agent", "语言",
        "Agent", "NLP", "机器", "识别", "生成", "分析",
    }
    found_keywords = [kw for kw in tech_keywords if kw in summary]
    if found_keywords:
        bonus = min(5, len(found_keywords) * 1)
        score = min(25.0, score + bonus)
        reasons.append(f"技术关键词x{len(found_keywords)} +{bonus}")

    return DimensionScore("摘要质量", round(score, 1), 25, "; ".join(reasons))


def evaluate_depth(entry: dict[str, Any]) -> DimensionScore:
    """Score technical depth from analysis.score (max 25)."""
    analysis = entry.get("analysis")
    if not isinstance(analysis, dict):
        return DimensionScore("技术深度", 0.0, 25, "缺少 analysis 字段")

    score_raw = analysis.get("score")
    if not isinstance(score_raw, (int, float)) or isinstance(score_raw, bool):
        return DimensionScore("技术深度", 0.0, 25, "缺少 score 或类型错误")

    clamped = max(1, min(10, score_raw))
    score = round((clamped - 1) / 9 * 25, 1)
    return DimensionScore("技术深度", score, 25, f"score={score_raw} → {score}分")


def evaluate_format(entry: dict[str, Any]) -> DimensionScore:
    """Score format compliance (max 20)."""
    score = 0.0
    reasons: list[str] = []

    for field in ("id", "title", "source_url", "status"):
        if isinstance(entry.get(field), str):
            score += 4.0
            reasons.append(f"{field}✓")
        else:
            reasons.append(f"{field}✗")

    has_created = "created_at" in entry and isinstance(entry["created_at"], str)
    has_updated = "updated_at" in entry and isinstance(entry["updated_at"], str)
    if has_created and has_updated:
        score += 4.0
        reasons.append("时间戳✓")
    else:
        reasons.append("时间戳✗")

    return DimensionScore("格式规范", score, 20, "; ".join(reasons))


def evaluate_tags(entry: dict[str, Any]) -> DimensionScore:
    """Score tag precision (max 15)."""
    tags = entry.get("tags")
    if not isinstance(tags, list) or len(tags) == 0:
        return DimensionScore("标签精度", 0.0, 15, "缺少 tags 或为空")

    n = len(tags)
    valid_count = sum(1 for t in tags if isinstance(t, str) and t in STANDARD_TAGS)
    reasons: list[str] = []

    if 1 <= n <= 3:
        base = 10.0
        reasons.append(f"标签数{n}(最优)")
    else:
        base = max(0.0, 10.0 - (n - 3) * 2)
        reasons.append(f"标签数{n}(最优1-3)")

    ratio = valid_count / n if n > 0 else 0
    bonus = round(ratio * 5, 1)
    reasons.append(f"标准标签{valid_count}/{n} +{bonus}")

    return DimensionScore("标签精度", min(15.0, base + bonus), 15, "; ".join(reasons))


def evaluate_buzzwords(entry: dict[str, Any]) -> DimensionScore:
    """Score buzzword absence (max 15)."""
    text_parts: list[str] = []
    for key in ("title", "summary"):
        val = entry.get(key)
        if isinstance(val, str):
            text_parts.append(val)

    analysis = entry.get("analysis")
    if isinstance(analysis, dict):
        for val in analysis.values():
            if isinstance(val, str):
                text_parts.append(val)
            elif isinstance(val, list):
                text_parts.extend(str(i) for i in val)

    combined = " ".join(text_parts)
    found = detect_buzzwords(combined)
    if found:
        penalty = min(15, len(found) * 3)
        score = max(0.0, 15.0 - penalty)
        return DimensionScore(
            "空洞词检测", score, 15,
            f"发现{len(found)}个: {', '.join(found)} 扣{penalty}分",
        )
    return DimensionScore("空洞词检测", 15.0, 15, "未检测到空洞词")


def evaluate_entry(entry: dict[str, Any]) -> QualityReport:
    """Run all 5 quality dimensions on a single entry."""
    dims = [
        evaluate_summary(entry),
        evaluate_depth(entry),
        evaluate_format(entry),
        evaluate_tags(entry),
        evaluate_buzzwords(entry),
    ]
    total = round(sum(d.score for d in dims), 1)
    return QualityReport(file_path="", total_score=total, dimensions=dims)


def print_progress(current: int, total: int, bar_len: int = 30) -> None:
    """Print an inline progress bar."""
    if total == 0:
        return
    fraction = current / total
    filled = int(bar_len * fraction)
    bar = "█" * filled + "░" * (bar_len - filled)
    sys.stdout.write(f"\r  [{bar}] {current}/{total}")
    sys.stdout.flush()
    if current == total:
        sys.stdout.write("\n")


def collect_json_files(args: list[str]) -> list[Path]:
    """Resolve input arguments into sorted JSON file paths."""
    files: list[Path] = []
    for arg in args:
        path = Path(arg)
        if path.is_file():
            files.append(path.resolve())
        elif "*" in arg:
            files.extend(
                p.resolve() for p in sorted(Path().glob(arg))
            )
        else:
            matched = sorted(Path().glob(arg))
            if matched:
                files.extend(p.resolve() for p in matched)
            else:
                files.append(path.resolve())
    seen: set[Path] = set()
    deduped: list[Path] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            deduped.append(f)
    return deduped


GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _grade_color(grade: str) -> str:
    if grade == "A":
        return GREEN
    if grade == "B":
        return YELLOW
    return RED


def _format_dimension(d: DimensionScore) -> str:
    bar_len = int(d.score / d.max_score * 10) if d.max_score > 0 else 0
    bar = "█" * bar_len + "░" * (10 - bar_len)
    return f"    {d.name:<12} {bar} {d.score:>5.1f}/{d.max_score:<4} {d.reason}"


def main() -> None:
    """Entry point."""
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <json_file> [json_file2 ...]")
        sys.exit(1)

    files = collect_json_files(sys.argv[1:])
    if not files:
        print("No JSON files found.")
        sys.exit(1)

    reports: list[QualityReport] = []
    has_c = False

    print(f"\n{'=' * 58}")
    print(f"  知识条目 5 维度质量评分")
    print(f"{'=' * 58}\n")

    for i, fp in enumerate(files, 1):
        print_progress(i, len(files))
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            dummy = DimensionScore("解析错误", 0.0, 0, str(exc))
            report = QualityReport(
                file_path=str(fp), total_score=0.0,
                dimensions=[DimensionScore(n, 0.0, 25, "文件无法解析")
                            for n in ("摘要质量", "技术深度", "格式规范", "标签精度", "空洞词检测")],
            )
            reports.append(report)
            continue

        entries = [data] if isinstance(data, dict) else data if isinstance(data, list) else []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            report = evaluate_entry(entry)
            report.file_path = str(fp)
            reports.append(report)

    print(f"\n{'=' * 58}")
    print(f"  {BOLD}评分结果{RESET}")
    print(f"{'=' * 58}\n")

    header = f"  {'文件':<42} {'总分':<7} {'等级':<4}"
    sep = f"  {'-' * 42} {'-' * 7} {'-' * 4}"
    print(header)
    print(sep)

    for r in reports:
        color = _grade_color(r.grade)
        print(f"  {r.file_path:<42} {r.total_score:<7} {color}{BOLD}{r.grade}{RESET}")
        for d in r.dimensions:
            print(_format_dimension(d))
        print()
        if r.grade == "C":
            has_c = True

    if has_c:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

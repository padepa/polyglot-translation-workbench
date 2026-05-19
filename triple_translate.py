#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三段式回译工具：
1. 中文 -> 英文
2. 英文 -> 日文
3. 日文 -> 中文

默认从剪贴板读取文本，也可以用命令行参数或标准输入传入文本。
"""

from __future__ import annotations

import argparse
import importlib
import sys
from dataclasses import dataclass
from types import ModuleType
from typing import Iterable

pyperclip: ModuleType | None = None
ts: ModuleType | None = None


DEFAULT_ENGINES = [
    "google",
    "youdao",
    "alibaba",
    "qqTranSmart",
    "sogou",
    "yandex",
    "papago",
    "iciba",
    "caiyun",
    "reverso",
    "translateCom",
]

KNOWN_ENGINES = [
    "alibaba",
    "apertium",
    "argos",
    "baidu",
    "bing",
    "caiyun",
    "cloudTranslation",
    "deepl",
    "elia",
    "google",
    "hujiang",
    "iciba",
    "iflytek",
    "iflyrec",
    "itranslate",
    "judic",
    "languageWire",
    "lara",
    "lingvanex",
    "niutrans",
    "mglip",
    "mirai",
    "modernMt",
    "myMemory",
    "papago",
    "qqFanyi",
    "qqTranSmart",
    "reverso",
    "sogou",
    "sysTran",
    "tilde",
    "translateCom",
    "translateMe",
    "utibet",
    "volcEngine",
    "xunjie",
    "yandex",
    "yeekit",
    "youdao",
]

LANGUAGE_CHAIN = [
    ("zh", "en", "中文 -> 英文"),
    ("en", "ja", "英文 -> 日文"),
    ("ja", "zh", "日文 -> 中文"),
]


@dataclass
class StepResult:
    label: str
    engine: str
    text: str


class TranslationFailed(RuntimeError):
    pass


def require_translation_dependencies() -> None:
    global ts
    if ts is None:
        try:
            ts = importlib.import_module("translators")
        except ImportError as exc:  # pragma: no cover - 只在未安装依赖时触发
            raise RuntimeError("缺少依赖：translators。请先运行：python -m pip install -r requirements.txt") from exc


def require_clipboard_dependency() -> None:
    global pyperclip
    if pyperclip is None:
        try:
            pyperclip = importlib.import_module("pyperclip")
        except ImportError as exc:  # pragma: no cover - 只在未安装依赖时触发
            raise RuntimeError("缺少依赖：pyperclip。请先运行：python -m pip install -r requirements.txt") from exc


def split_engines(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_ENGINES)

    if raw.strip().lower() in {"all", "*"}:
        require_translation_dependencies()
        return list(ts.translators_pool)

    engines = [item.strip() for item in raw.split(",") if item.strip()]
    if not engines:
        raise ValueError("翻译引擎列表为空。")
    return engines


def get_input_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text

    if args.stdin:
        return sys.stdin.read().strip()

    require_clipboard_dependency()
    clipboard_text = pyperclip.paste().strip()
    if clipboard_text:
        return clipboard_text

    raise ValueError("没有读到文本。请先复制一段话，或使用 --text / --stdin。")


def clean_result(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("data") or value.get("translation") or value.get("text") or str(value)
    return str(value).strip()


def translate_once(
    text: str,
    from_language: str,
    to_language: str,
    engines: Iterable[str],
    timeout: float,
) -> tuple[str, str]:
    require_translation_dependencies()

    errors: list[str] = []

    for engine in engines:
        try:
            result = ts.translate_text(
                text,
                translator=engine,
                from_language=from_language,
                to_language=to_language,
                timeout=timeout,
                if_print_warning=False,
            )
            translated = clean_result(result)
            if translated:
                return translated, engine
            errors.append(f"{engine}: 返回空结果")
        except Exception as exc:  # noqa: BLE001 - 这里需要逐个引擎容错
            errors.append(f"{engine}: {type(exc).__name__}: {str(exc)[:120]}")

    raise TranslationFailed("所有翻译引擎都失败：\n" + "\n".join(errors))


def triple_translate(text: str, engines: list[str], timeout: float) -> list[StepResult]:
    current = text
    results: list[StepResult] = []

    for from_language, to_language, label in LANGUAGE_CHAIN:
        current, engine = translate_once(current, from_language, to_language, engines, timeout)
        results.append(StepResult(label=label, engine=engine, text=current))

    return results


def translate_with_single_engine(text: str, engine: str, timeout: float) -> list[StepResult] | None:
    try:
        return triple_translate(text, [engine], timeout)
    except TranslationFailed:
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="把中文文本按 中文->英文->日文->中文 连续翻译三次，并返回最终中文结果。"
    )
    parser.add_argument("--text", help="直接传入要翻译的文本。默认读取剪贴板。")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取文本。")
    parser.add_argument(
        "--engines",
        default=",".join(DEFAULT_ENGINES),
        help="逗号分隔的翻译引擎列表，按顺序尝试。默认会尝试多个公共引擎。",
    )
    parser.add_argument("--timeout", type=float, default=12.0, help="单次请求超时时间，默认 12 秒。")
    parser.add_argument("--show-steps", action="store_true", help="显示三次中间翻译结果。")
    parser.add_argument("--copy", action="store_true", help="把最终结果复制回剪贴板。")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="让每个引擎独立完成三连翻译，输出多个最终结果用于对比。",
    )
    parser.add_argument("--list-engines", action="store_true", help="列出当前库支持的全部翻译引擎。")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.list_engines:
            require_translation_dependencies()
            print(",".join(ts.translators_pool))
            return 0

        text = get_input_text(args)
        engines = split_engines(args.engines)

        if args.compare:
            output_lines = ["原文：", text, "", "不同引擎三连翻译结果："]
            ok_count = 0
            for engine in engines:
                results = translate_with_single_engine(text, engine, args.timeout)
                if not results:
                    output_lines.extend(["", f"[{engine}] 失败或不可用"])
                    continue
                ok_count += 1
                output_lines.extend(["", f"[{engine}]", results[-1].text])
                if args.show_steps:
                    for step in results:
                        output_lines.append(f"  - {step.label}: {step.text}")
            if ok_count == 0:
                raise TranslationFailed("没有任何引擎完成三连翻译。")

            output_text = "\n".join(output_lines)
            print(output_text)
            if args.copy:
                require_clipboard_dependency()
                pyperclip.copy(output_text)
                print("\n已复制对比结果到剪贴板。", file=sys.stderr)
            return 0

        results = triple_translate(text, engines, args.timeout)
        final_text = results[-1].text

        if args.show_steps:
            print("原文：")
            print(text)
            for step in results:
                print(f"\n{step.label}（{step.engine}）：")
                print(step.text)
            print("\n最终结果：")

        print(final_text)

        if args.copy:
            require_clipboard_dependency()
            pyperclip.copy(final_text)
            print("\n已复制最终结果到剪贴板。", file=sys.stderr)

        return 0
    except Exception as exc:  # noqa: BLE001 - 命令行入口统一输出错误
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

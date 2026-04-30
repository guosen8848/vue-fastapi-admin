import re
from copy import deepcopy

from fastapi import HTTPException

from app.exam.constants import (
    EXAM_IMPORT_HEADERS,
    EXAM_OBJECTIVE_TYPES,
    EXAM_OPTION_KEYS,
    EXAM_SUBJECTIVE_TYPES,
    EXAM_TRUE_FALSE_OPTIONS,
    ExamDifficulty,
    ExamQuestionType,
)


QUESTION_TYPE_ALIASES = {
    "single_choice": ExamQuestionType.SINGLE_CHOICE,
    "单选题": ExamQuestionType.SINGLE_CHOICE,
    "multiple_choice": ExamQuestionType.MULTIPLE_CHOICE,
    "多选题": ExamQuestionType.MULTIPLE_CHOICE,
    "true_false": ExamQuestionType.TRUE_FALSE,
    "判断题": ExamQuestionType.TRUE_FALSE,
    "fill_blank": ExamQuestionType.FILL_BLANK,
    "填空题": ExamQuestionType.FILL_BLANK,
    "short_answer": ExamQuestionType.SHORT_ANSWER,
    "简答题": ExamQuestionType.SHORT_ANSWER,
}

DIFFICULTY_ALIASES = {
    "simple": ExamDifficulty.SIMPLE,
    "简单": ExamDifficulty.SIMPLE,
    "medium": ExamDifficulty.MEDIUM,
    "中等": ExamDifficulty.MEDIUM,
    "hard": ExamDifficulty.HARD,
    "困难": ExamDifficulty.HARD,
}

TRUE_FALSE_ALIASES = {
    "true": "TRUE",
    "false": "FALSE",
    "正确": "TRUE",
    "错误": "FALSE",
    "对": "TRUE",
    "错": "FALSE",
    "是": "TRUE",
    "否": "FALSE",
    "1": "TRUE",
    "0": "FALSE",
}


def normalize_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def normalize_optional_text(value):
    text = normalize_text(value)
    return text or None


def round_score(value):
    return round(float(value or 0), 2)


def split_tags(value):
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = str(value).replace("，", ",").split(",")
    tags = []
    seen = set()
    for item in items:
        text = normalize_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        tags.append(text)
    return tags


def parse_question_type(value):
    text = normalize_text(value)
    question_type = QUESTION_TYPE_ALIASES.get(text)
    if not question_type:
        raise HTTPException(status_code=400, detail="题型不合法")
    return question_type


def parse_difficulty(value):
    text = normalize_text(value)
    if not text:
        return ExamDifficulty.MEDIUM
    difficulty = DIFFICULTY_ALIASES.get(text)
    if not difficulty:
        raise HTTPException(status_code=400, detail="难度不合法")
    return difficulty


def build_true_false_options():
    return deepcopy(EXAM_TRUE_FALSE_OPTIONS)


def split_correct_answer_values(question_type: ExamQuestionType, correct_answer):
    if isinstance(correct_answer, list):
        return correct_answer

    text = normalize_text(correct_answer).upper()
    if not text:
        return []

    normalized_text = text.replace("，", ",").replace("、", ",")
    raw_values = [item for item in re.split(r"[\s,]+", normalized_text) if item]

    if question_type == ExamQuestionType.MULTIPLE_CHOICE and len(raw_values) == 1:
        compact_value = raw_values[0]
        if len(compact_value) > 1 and all(char in EXAM_OPTION_KEYS for char in compact_value):
            return list(compact_value)

    return raw_values


def normalize_option_list(question_type: ExamQuestionType, raw_options):
    if question_type == ExamQuestionType.TRUE_FALSE:
        return build_true_false_options()
    if question_type in EXAM_SUBJECTIVE_TYPES:
        return []

    options = []
    seen_keys = set()
    for index, item in enumerate(raw_options or [], start=1):
        option_key = normalize_text(item.get("option_key")) or EXAM_OPTION_KEYS[index - 1]
        option_key = option_key.upper()
        option_content = normalize_text(item.get("option_content"))
        if not option_content:
            continue
        if option_key not in EXAM_OPTION_KEYS:
            raise HTTPException(status_code=400, detail="选择题选项键仅支持 A-F")
        if option_key in seen_keys:
            raise HTTPException(status_code=400, detail="选择题选项键重复")
        seen_keys.add(option_key)
        options.append({"option_key": option_key, "option_content": option_content})

    options.sort(key=lambda item: EXAM_OPTION_KEYS.index(item["option_key"]))
    if len(options) < 2:
        raise HTTPException(status_code=400, detail="选择题至少需要两个有效选项")
    return options


def normalize_correct_answer(question_type: ExamQuestionType, correct_answer, options):
    if question_type in EXAM_SUBJECTIVE_TYPES:
        return []

    if question_type == ExamQuestionType.TRUE_FALSE:
        if isinstance(correct_answer, list):
            raw_values = [normalize_text(item).lower() for item in correct_answer if normalize_text(item)]
        else:
            raw_values = [normalize_text(correct_answer).lower()] if normalize_text(correct_answer) else []
        if len(raw_values) != 1:
            raise HTTPException(status_code=400, detail="判断题正确答案必须且只能填写一个值")
        normalized_value = TRUE_FALSE_ALIASES.get(raw_values[0])
        if not normalized_value:
            raise HTTPException(status_code=400, detail="判断题正确答案仅支持 正确/错误")
        return [normalized_value]

    valid_option_keys = [item["option_key"] for item in options]
    raw_values = split_correct_answer_values(question_type, correct_answer)

    answers = []
    for raw_value in raw_values:
        text = normalize_text(raw_value).upper()
        if not text or text in answers:
            continue
        answers.append(text)

    if question_type == ExamQuestionType.SINGLE_CHOICE and len(answers) != 1:
        raise HTTPException(status_code=400, detail="单选题正确答案必须且只能填写一个值")
    if question_type == ExamQuestionType.MULTIPLE_CHOICE and not answers:
        raise HTTPException(status_code=400, detail="多选题必须填写至少一个正确答案")

    for answer in answers:
        if answer not in valid_option_keys:
            raise HTTPException(status_code=400, detail="正确答案超出已有选项范围")

    answers.sort(key=lambda item: EXAM_OPTION_KEYS.index(item))
    return answers


def normalize_question_payload(data: dict):
    question_type = parse_question_type(data.get("question_type"))
    stem = normalize_text(data.get("stem"))
    if not stem:
        raise HTTPException(status_code=400, detail="题干不能为空")

    default_score = round_score(data.get("default_score"))
    if default_score <= 0:
        raise HTTPException(status_code=400, detail="分值必须大于 0")

    options = normalize_option_list(question_type, data.get("options"))
    correct_answer = normalize_correct_answer(question_type, data.get("correct_answer"), options)

    return {
        "bank_id": int(data.get("bank_id")),
        "question_type": question_type,
        "category_path": normalize_optional_text(data.get("category_path")),
        "stem": stem,
        "options": options,
        "correct_answer": correct_answer,
        "reference_answer": normalize_optional_text(data.get("reference_answer")),
        "analysis": normalize_optional_text(data.get("analysis")),
        "tags": split_tags(data.get("tags")),
        "difficulty": parse_difficulty(data.get("difficulty")),
        "default_score": default_score,
        "is_active": bool(data.get("is_active", True)),
    }


def build_question_snapshot(data: dict):
    question_type = data["question_type"]
    question_type_value = question_type.value if isinstance(question_type, ExamQuestionType) else str(question_type)
    difficulty = data["difficulty"]
    difficulty_value = difficulty.value if isinstance(difficulty, ExamDifficulty) else str(difficulty)

    return {
        "question_id": int(data["id"]),
        "bank_id": int(data["bank_id"]),
        "question_type": question_type_value,
        "category_path": data.get("category_path"),
        "stem": data.get("stem") or "",
        "options": deepcopy(data.get("options") or []),
        "correct_answer": deepcopy(data.get("correct_answer") or []),
        "reference_answer": data.get("reference_answer"),
        "analysis": data.get("analysis"),
        "tags": deepcopy(data.get("tags") or []),
        "difficulty": difficulty_value,
        "default_score": round_score(data.get("default_score")),
        "is_active": bool(data.get("is_active", True)),
    }


def with_paper_question_snapshot(question_snapshot: dict, score: float, sort_order: int, paper_question_id: int | None = None):
    payload = deepcopy(question_snapshot)
    payload["score"] = round_score(score)
    payload["sort_order"] = int(sort_order)
    if paper_question_id is not None:
        payload["paper_question_id"] = int(paper_question_id)
    return payload


def sanitize_question_snapshot(snapshot: dict, reveal_answer: bool = False):
    payload = deepcopy(snapshot)
    if not reveal_answer:
        payload.pop("correct_answer", None)
        payload.pop("reference_answer", None)
        payload.pop("analysis", None)
    return payload


def is_objective_question(question_type: ExamQuestionType | str):
    normalized = ExamQuestionType(question_type)
    return normalized in EXAM_OBJECTIVE_TYPES


def normalize_user_answer(question_type: ExamQuestionType | str, answer_payload):
    normalized_type = ExamQuestionType(question_type)

    if normalized_type in EXAM_SUBJECTIVE_TYPES:
        if isinstance(answer_payload, dict):
            return normalize_text(answer_payload.get("text"))
        return normalize_text(answer_payload)

    if normalized_type == ExamQuestionType.TRUE_FALSE:
        if isinstance(answer_payload, list):
            raw_values = [normalize_text(item).lower() for item in answer_payload if normalize_text(item)]
        else:
            raw_text = normalize_text(answer_payload)
            raw_values = [raw_text.lower()] if raw_text else []
        if not raw_values:
            return []
        normalized_value = TRUE_FALSE_ALIASES.get(raw_values[0])
        return [normalized_value] if normalized_value else []

    if isinstance(answer_payload, list):
        raw_values = answer_payload
    else:
        raw_text = normalize_text(answer_payload)
        raw_values = raw_text.replace("，", ",").split(",") if raw_text else []

    answers = []
    for raw_value in raw_values:
        value = normalize_text(raw_value).upper()
        if not value or value in answers:
            continue
        answers.append(value)

    answers.sort(key=lambda item: EXAM_OPTION_KEYS.index(item) if item in EXAM_OPTION_KEYS else item)
    if normalized_type == ExamQuestionType.SINGLE_CHOICE:
        return answers[:1]
    return answers


def build_import_row_payload(row_data: dict):
    options = []
    for option_key in EXAM_OPTION_KEYS:
        options.append(
            {
                "option_key": option_key,
                "option_content": row_data.get(f"选项{option_key}"),
            }
        )

    return {
        "question_type": row_data.get("题型"),
        "category_path": row_data.get("题目分类"),
        "stem": row_data.get("题干"),
        "options": options,
        "correct_answer": row_data.get("正确答案"),
        "default_score": row_data.get("分值"),
        "difficulty": row_data.get("难度"),
        "analysis": row_data.get("解析"),
        "reference_answer": row_data.get("参考答案"),
        "tags": row_data.get("标签"),
    }


def validate_import_headers(headers: list[str]):
    normalized_headers = [normalize_text(item) for item in headers]
    missing_headers = [header for header in EXAM_IMPORT_HEADERS if header not in normalized_headers]
    if missing_headers:
        raise HTTPException(status_code=400, detail=f"题库模板缺少表头: {', '.join(missing_headers)}")

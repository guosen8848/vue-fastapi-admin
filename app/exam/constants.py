from enum import StrEnum


class ExamQuestionType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"


class ExamPaperStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class ExamAttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    PENDING_REVIEW = "pending_review"
    GRADED = "graded"


class ExamJudgeStatus(StrEnum):
    AUTO_CORRECT = "auto_correct"
    AUTO_WRONG = "auto_wrong"
    MANUAL_PENDING = "manual_pending"
    MANUAL_DONE = "manual_done"


class ExamPracticeSessionStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ExamDifficulty(StrEnum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    HARD = "hard"


EXAM_OPTION_KEYS = ("A", "B", "C", "D", "E", "F")

EXAM_IMPORT_SHEET_NAME = "questions"

EXAM_IMPORT_HEADERS = [
    "题型",
    "题目分类",
    "题干",
    "选项A",
    "选项B",
    "选项C",
    "选项D",
    "选项E",
    "选项F",
    "正确答案",
    "分值",
    "难度",
    "解析",
    "参考答案",
    "标签",
]

EXAM_OBJECTIVE_TYPES = {
    ExamQuestionType.SINGLE_CHOICE,
    ExamQuestionType.MULTIPLE_CHOICE,
    ExamQuestionType.TRUE_FALSE,
}

EXAM_SUBJECTIVE_TYPES = {
    ExamQuestionType.FILL_BLANK,
    ExamQuestionType.SHORT_ANSWER,
}

EXAM_TRUE_FALSE_OPTIONS = [
    {"option_key": "TRUE", "option_content": "正确"},
    {"option_key": "FALSE", "option_content": "错误"},
]

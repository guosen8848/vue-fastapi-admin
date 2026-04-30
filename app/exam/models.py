from tortoise import fields

from app.exam.constants import (
    ExamAttemptStatus,
    ExamDifficulty,
    ExamJudgeStatus,
    ExamPaperStatus,
    ExamPracticeSessionStatus,
    ExamQuestionType,
)
from app.models.base import BaseModel, TimestampMixin


class ExamBank(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=100, unique=True, description="题库名称", index=True)
    desc = fields.CharField(max_length=500, null=True, description="题库说明")
    source_file_name = fields.CharField(max_length=255, null=True, description="原始文件名")
    source_file_path = fields.CharField(max_length=500, null=True, description="原始文件路径")
    question_count = fields.IntField(default=0, description="题目数量", index=True)
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)
    created_by = fields.IntField(null=True, description="创建人ID", index=True)
    updated_by = fields.IntField(null=True, description="更新人ID", index=True)

    class Meta:
        table = "exam_bank"


class ExamQuestion(BaseModel, TimestampMixin):
    bank_id = fields.IntField(description="所属题库ID", index=True)
    question_type = fields.CharEnumField(ExamQuestionType, description="题型", index=True)
    category_path = fields.CharField(max_length=255, null=True, description="题目分类路径", index=True)
    stem = fields.TextField(description="题干")
    options = fields.JSONField(null=True, description="题目选项")
    correct_answer = fields.JSONField(null=True, description="标准答案")
    reference_answer = fields.TextField(null=True, description="参考答案")
    analysis = fields.TextField(null=True, description="解析")
    tags = fields.JSONField(null=True, description="标签")
    difficulty = fields.CharEnumField(
        ExamDifficulty,
        default=ExamDifficulty.MEDIUM,
        description="难度",
        index=True,
    )
    default_score = fields.FloatField(default=0, description="默认分值")
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)
    created_by = fields.IntField(null=True, description="创建人ID", index=True)
    updated_by = fields.IntField(null=True, description="更新人ID", index=True)

    class Meta:
        table = "exam_question"


class ExamPaper(BaseModel, TimestampMixin):
    title = fields.CharField(max_length=200, description="试卷标题", index=True)
    desc = fields.CharField(max_length=500, null=True, description="试卷说明")
    status = fields.CharEnumField(ExamPaperStatus, default=ExamPaperStatus.DRAFT, description="试卷状态", index=True)
    duration_minutes = fields.IntField(default=0, description="限时分钟数")
    pass_score = fields.FloatField(default=0, description="及格分")
    total_score = fields.FloatField(default=0, description="总分")
    question_count = fields.IntField(default=0, description="题目数量")
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)
    created_by = fields.IntField(null=True, description="创建人ID", index=True)
    updated_by = fields.IntField(null=True, description="更新人ID", index=True)

    class Meta:
        table = "exam_paper"


class ExamPaperQuestion(BaseModel, TimestampMixin):
    paper_id = fields.IntField(description="试卷ID", index=True)
    question_id = fields.IntField(description="题目ID", index=True)
    sort_order = fields.IntField(default=0, description="排序", index=True)
    score = fields.FloatField(default=0, description="题目分值")
    question_snapshot = fields.JSONField(description="题目快照")

    class Meta:
        table = "exam_paper_question"
        unique_together = (("paper_id", "question_id"),)


class ExamAttempt(BaseModel, TimestampMixin):
    paper_id = fields.IntField(description="试卷ID", index=True)
    user_id = fields.IntField(description="答题人ID", index=True)
    status = fields.CharEnumField(
        ExamAttemptStatus,
        default=ExamAttemptStatus.IN_PROGRESS,
        description="答卷状态",
        index=True,
    )
    objective_score = fields.FloatField(default=0, description="客观题得分")
    subjective_score = fields.FloatField(default=0, description="主观题得分")
    total_score = fields.FloatField(default=0, description="总分")
    started_at = fields.DatetimeField(auto_now_add=True, description="开始时间", index=True)
    submitted_at = fields.DatetimeField(null=True, description="提交时间", index=True)
    graded_at = fields.DatetimeField(null=True, description="阅卷完成时间", index=True)
    graded_by = fields.IntField(null=True, description="阅卷人ID", index=True)
    claimed_by = fields.IntField(null=True, description="领取阅卷人ID", index=True)
    claimed_by_name = fields.CharField(max_length=64, null=True, description="领取阅卷人名称")

    class Meta:
        table = "exam_attempt"
        unique_together = (("paper_id", "user_id"),)


class ExamAnswer(BaseModel, TimestampMixin):
    attempt_id = fields.IntField(description="答卷ID", index=True)
    paper_question_id = fields.IntField(description="试卷题目ID", index=True)
    question_id = fields.IntField(description="原题ID", index=True)
    question_type = fields.CharEnumField(ExamQuestionType, description="题型", index=True)
    answer_payload = fields.JSONField(null=True, description="用户答案")
    judge_status = fields.CharEnumField(ExamJudgeStatus, null=True, description="判题状态", index=True)
    is_correct = fields.BooleanField(null=True, description="是否答对", index=True)
    auto_score = fields.FloatField(default=0, description="自动判分")
    manual_score = fields.FloatField(default=0, description="人工判分")
    final_score = fields.FloatField(default=0, description="最终得分")
    reviewer_comment = fields.TextField(null=True, description="阅卷备注")
    answer_snapshot = fields.JSONField(description="答题快照")
    judged_at = fields.DatetimeField(null=True, description="判题时间", index=True)
    judged_by = fields.IntField(null=True, description="判题人ID", index=True)

    class Meta:
        table = "exam_answer"
        unique_together = (("attempt_id", "paper_question_id"),)


class ExamPracticeSession(BaseModel, TimestampMixin):
    user_id = fields.IntField(description="练习人ID", index=True)
    bank_id = fields.IntField(null=True, description="题库ID", index=True)
    question_type = fields.CharEnumField(ExamQuestionType, null=True, description="题型", index=True)
    difficulty = fields.CharEnumField(ExamDifficulty, null=True, description="难度", index=True)
    status = fields.CharEnumField(
        ExamPracticeSessionStatus,
        default=ExamPracticeSessionStatus.IN_PROGRESS,
        description="练习状态",
        index=True,
    )
    question_count = fields.IntField(default=0, description="题目数量")
    answered_count = fields.IntField(default=0, description="已答题数")
    correct_count = fields.IntField(default=0, description="答对题数")
    wrong_count = fields.IntField(default=0, description="答错题数")
    started_at = fields.DatetimeField(auto_now_add=True, description="开始时间", index=True)
    finished_at = fields.DatetimeField(null=True, description="完成时间", index=True)

    class Meta:
        table = "exam_practice_session"


class ExamPracticeAnswer(BaseModel, TimestampMixin):
    session_id = fields.IntField(description="练习ID", index=True)
    question_id = fields.IntField(description="题目ID", index=True)
    question_type = fields.CharEnumField(ExamQuestionType, description="题型", index=True)
    answer_snapshot = fields.JSONField(description="题目快照")
    answer_payload = fields.JSONField(null=True, description="用户答案")
    is_correct = fields.BooleanField(null=True, description="是否答对", index=True)
    sort_order = fields.IntField(default=0, description="题目排序", index=True)
    answered_at = fields.DatetimeField(null=True, description="作答时间", index=True)

    class Meta:
        table = "exam_practice_answer"
        unique_together = (("session_id", "question_id"),)


class ExamPracticeWrongQuestion(BaseModel, TimestampMixin):
    user_id = fields.IntField(description="用户ID", index=True)
    question_id = fields.IntField(description="题目ID", index=True)
    wrong_count = fields.IntField(default=0, description="答错次数")
    correct_count = fields.IntField(default=0, description="答对次数")
    last_wrong_at = fields.DatetimeField(null=True, description="最近答错时间", index=True)
    mastered_at = fields.DatetimeField(null=True, description="掌握时间", index=True)

    class Meta:
        table = "exam_practice_wrong_question"
        unique_together = (("user_id", "question_id"),)

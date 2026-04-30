from fastapi import HTTPException
from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.exam.models import ExamBank, ExamPaperQuestion, ExamQuestion
from app.exam.schemas.question import ExamQuestionCreate, ExamQuestionUpdate
from app.exam.utils import build_question_snapshot, normalize_question_payload


class ExamQuestionController(CRUDBase[ExamQuestion, ExamQuestionCreate, ExamQuestionUpdate]):
    def __init__(self):
        super().__init__(model=ExamQuestion)

    async def _validate_bank(self, bank_id: int, active_only: bool = False):
        query = ExamBank.filter(id=bank_id)
        if active_only:
            query = query.filter(is_active=True)
        bank = await query.first()
        if not bank:
            raise HTTPException(status_code=404, detail="所属题库不存在")
        return bank

    def _normalize_serialized_question(self, data: dict, bank_map: dict[int, dict] | None = None, referenced_ids=None):
        data["options"] = data.get("options") or []
        data["correct_answer"] = data.get("correct_answer") or []
        data["tags"] = data.get("tags") or []
        bank_info = (bank_map or {}).get(data["bank_id"], {})
        data["bank"] = bank_info
        data["bank_name"] = bank_info.get("name")
        data["referenced"] = data["id"] in (referenced_ids or set())
        return data

    async def serialize_question(self, question: ExamQuestion, bank_map: dict[int, dict] | None = None, referenced_ids=None):
        data = await question.to_dict()
        return self._normalize_serialized_question(data, bank_map=bank_map, referenced_ids=referenced_ids)

    async def build_snapshot(self, question: ExamQuestion):
        data = await question.to_dict()
        normalized = self._normalize_serialized_question(data)
        return build_question_snapshot(normalized)

    async def get_questions_by_ids(self, question_ids: list[int], active_only: bool = False):
        unique_ids = list(dict.fromkeys(question_ids))
        if not unique_ids:
            return {}

        query = ExamQuestion.filter(id__in=unique_ids)
        if active_only:
            active_bank_ids = await ExamBank.filter(is_active=True).values_list("id", flat=True)
            query = query.filter(is_active=True, bank_id__in=list(active_bank_ids))
        question_objs = await query.all()
        question_map = {obj.id: obj for obj in question_objs}
        if len(question_map) != len(unique_ids):
            raise HTTPException(status_code=400, detail="存在不存在或不可用的题目")
        return question_map

    async def list_questions(
        self,
        page: int,
        page_size: int,
        bank_id: int | None = None,
        question_type: str | None = None,
        difficulty: str | None = None,
        is_active: bool | None = None,
        stem: str | None = None,
        category_path: str | None = None,
        selectable_only: bool = False,
    ):
        q = Q()
        if bank_id is not None:
            q &= Q(bank_id=bank_id)
        if question_type:
            q &= Q(question_type=question_type)
        if difficulty:
            q &= Q(difficulty=difficulty)
        if is_active is not None:
            q &= Q(is_active=is_active)
        if stem:
            q &= Q(stem__contains=stem)
        if category_path:
            q &= Q(category_path__contains=category_path)
        if selectable_only:
            active_bank_ids = await ExamBank.filter(is_active=True).values_list("id", flat=True)
            q &= Q(is_active=True, bank_id__in=list(active_bank_ids))

        total, question_objs = await self.list(page=page, page_size=page_size, search=q, order=["-id"])
        data = [await obj.to_dict() for obj in question_objs]
        bank_ids = list({item["bank_id"] for item in data})
        question_ids = [item["id"] for item in data]
        bank_rows = await ExamBank.filter(id__in=bank_ids).values("id", "name", "is_active")
        referenced_ids = set(await ExamPaperQuestion.filter(question_id__in=question_ids).values_list("question_id", flat=True))
        bank_map = {item["id"]: item for item in bank_rows}
        data = [self._normalize_serialized_question(item, bank_map=bank_map, referenced_ids=referenced_ids) for item in data]
        return total, data

    async def get_question_detail(self, question_id: int):
        question = await self.get(id=question_id)
        bank = await self._validate_bank(question.bank_id)
        referenced = await ExamPaperQuestion.filter(question_id=question_id).exists()
        return await self.serialize_question(
            question,
            bank_map={bank.id: {"id": bank.id, "name": bank.name, "is_active": bank.is_active}},
            referenced_ids={question_id} if referenced else set(),
        )

    async def create_question(self, obj_in: ExamQuestionCreate, user_id: int):
        payload = normalize_question_payload(obj_in.model_dump())
        await self._validate_bank(payload["bank_id"])
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        return await self.create(obj_in=payload)

    async def update_question(self, obj_in: ExamQuestionUpdate, user_id: int):
        await self.get(id=obj_in.id)
        payload = normalize_question_payload(obj_in.model_dump())
        await self._validate_bank(payload["bank_id"])
        payload["updated_by"] = user_id
        return await self.update(id=obj_in.id, obj_in=payload)

    async def delete_question(self, question_id: int):
        referenced = await ExamPaperQuestion.filter(question_id=question_id).exists()
        if referenced:
            raise HTTPException(status_code=400, detail="题目已经被试卷引用，无法删除")
        await self.remove(id=question_id)


exam_question_controller = ExamQuestionController()

from io import BytesIO

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.core.ctx import CTX_USER_ID
from app.exam.controllers import (
    exam_attempt_controller,
    exam_bank_controller,
    exam_dashboard_controller,
    exam_grading_controller,
    exam_paper_controller,
    exam_practice_controller,
    exam_question_controller,
)
from app.exam.schemas import (
    ExamAttemptSavePayload,
    ExamAttemptStartPayload,
    ExamAttemptSubmitPayload,
    ExamBankCreate,
    ExamBankUpdate,
    ExamGradingClaimPayload,
    ExamGradingCompletePayload,
    ExamGradingScorePayload,
    ExamPaperActionPayload,
    ExamPaperCreate,
    ExamPaperUpdate,
    ExamPracticeActionPayload,
    ExamPracticeAnswerPayload,
    ExamPracticeStartPayload,
    ExamQuestionCreate,
    ExamQuestionUpdate,
)
from app.schemas.base import Success, SuccessExtra

router = APIRouter()


@router.get("/dashboard", summary="查看考试首页汇总")
async def get_exam_dashboard():
    data = await exam_dashboard_controller.get_dashboard(user_id=CTX_USER_ID.get())
    return Success(data=data)


@router.get("/bank/list", summary="查看题库列表")
async def list_exam_banks(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    name: str | None = Query(None, description="题库名称"),
    is_active: bool | None = Query(None, description="是否启用"),
):
    total, data = await exam_bank_controller.list_banks(page=page, page_size=page_size, name=name, is_active=is_active)
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/bank/get", summary="查看题库详情")
async def get_exam_bank(bank_id: int = Query(..., description="题库ID")):
    data = await exam_bank_controller.get_bank_detail(bank_id=bank_id)
    return Success(data=data)


@router.post("/bank/create", summary="创建题库")
async def create_exam_bank(bank_in: ExamBankCreate):
    await exam_bank_controller.create_bank(obj_in=bank_in, user_id=CTX_USER_ID.get())
    return Success(msg="Created Successfully")


@router.post("/bank/update", summary="更新题库")
async def update_exam_bank(bank_in: ExamBankUpdate):
    await exam_bank_controller.update_bank(obj_in=bank_in, user_id=CTX_USER_ID.get())
    return Success(msg="Updated Successfully")


@router.delete("/bank/delete", summary="删除题库")
async def delete_exam_bank(bank_id: int = Query(..., description="题库ID")):
    await exam_bank_controller.delete_bank(bank_id=bank_id)
    return Success(msg="Deleted Successfully")


@router.get("/bank/template", summary="下载题库模板")
async def download_exam_bank_template():
    stream = exam_bank_controller.build_template_file()
    return StreamingResponse(
        BytesIO(stream.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="exam_question_template.xlsx"'},
    )


@router.post("/bank/import", summary="导入题库")
async def import_exam_bank(
    name: str = Form(..., description="题库名称"),
    desc: str | None = Form(None, description="题库说明"),
    is_active: bool = Form(True, description="是否启用"),
    file: UploadFile = File(..., description="题库文件"),
):
    data = await exam_bank_controller.import_bank_questions(
        name=name,
        desc=desc,
        is_active=is_active,
        file=file,
        user_id=CTX_USER_ID.get(),
    )
    return Success(data=data, msg="Import Finished")


@router.get("/question/list", summary="查看题目列表")
async def list_exam_questions(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    bank_id: int | None = Query(None, description="题库ID"),
    question_type: str | None = Query(None, description="题型"),
    difficulty: str | None = Query(None, description="难度"),
    is_active: bool | None = Query(None, description="是否启用"),
    stem: str | None = Query(None, description="题干关键字"),
    category_path: str | None = Query(None, description="分类路径"),
    selectable_only: bool = Query(False, description="仅返回可组卷题目"),
):
    total, data = await exam_question_controller.list_questions(
        page=page,
        page_size=page_size,
        bank_id=bank_id,
        question_type=question_type,
        difficulty=difficulty,
        is_active=is_active,
        stem=stem,
        category_path=category_path,
        selectable_only=selectable_only,
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/question/get", summary="查看题目详情")
async def get_exam_question(question_id: int = Query(..., description="题目ID")):
    data = await exam_question_controller.get_question_detail(question_id=question_id)
    return Success(data=data)


@router.post("/question/create", summary="创建题目")
async def create_exam_question(question_in: ExamQuestionCreate):
    await exam_question_controller.create_question(obj_in=question_in, user_id=CTX_USER_ID.get())
    return Success(msg="Created Successfully")


@router.post("/question/update", summary="更新题目")
async def update_exam_question(question_in: ExamQuestionUpdate):
    await exam_question_controller.update_question(obj_in=question_in, user_id=CTX_USER_ID.get())
    return Success(msg="Updated Successfully")


@router.delete("/question/delete", summary="删除题目")
async def delete_exam_question(question_id: int = Query(..., description="题目ID")):
    await exam_question_controller.delete_question(question_id=question_id)
    return Success(msg="Deleted Successfully")


@router.get("/paper/list", summary="查看试卷列表")
async def list_exam_papers(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    title: str | None = Query(None, description="试卷标题"),
    status: str | None = Query(None, description="试卷状态"),
    is_active: bool | None = Query(None, description="是否启用"),
):
    total, data = await exam_paper_controller.list_papers(
        page=page,
        page_size=page_size,
        title=title,
        status=status,
        is_active=is_active,
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/paper/get", summary="查看试卷详情")
async def get_exam_paper(paper_id: int = Query(..., description="试卷ID")):
    data = await exam_paper_controller.get_paper_detail(paper_id=paper_id)
    return Success(data=data)


@router.get("/paper/attempts", summary="查看试卷作答情况")
async def get_exam_paper_attempts(paper_id: int = Query(..., description="试卷ID")):
    data = await exam_paper_controller.get_paper_attempts(paper_id=paper_id)
    return Success(data=data)


@router.post("/paper/create", summary="创建试卷")
async def create_exam_paper(paper_in: ExamPaperCreate):
    await exam_paper_controller.create_paper(obj_in=paper_in, user_id=CTX_USER_ID.get())
    return Success(msg="Created Successfully")


@router.post("/paper/update", summary="更新试卷")
async def update_exam_paper(paper_in: ExamPaperUpdate):
    await exam_paper_controller.update_paper(obj_in=paper_in, user_id=CTX_USER_ID.get())
    return Success(msg="Updated Successfully")


@router.delete("/paper/delete", summary="删除试卷")
async def delete_exam_paper(paper_id: int = Query(..., description="试卷ID")):
    await exam_paper_controller.delete_paper(paper_id=paper_id)
    return Success(msg="Deleted Successfully")


@router.post("/paper/publish", summary="发布试卷")
async def publish_exam_paper(payload: ExamPaperActionPayload):
    await exam_paper_controller.publish_paper(paper_id=payload.paper_id)
    return Success(msg="Published Successfully")


@router.post("/paper/close", summary="关闭试卷")
async def close_exam_paper(payload: ExamPaperActionPayload):
    await exam_paper_controller.close_paper(paper_id=payload.paper_id)
    return Success(msg="Closed Successfully")


@router.get("/answer/paper/list", summary="查看可答试卷列表")
async def list_answerable_exam_papers(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    title: str | None = Query(None, description="试卷标题"),
):
    total, data = await exam_attempt_controller.list_answerable_papers(
        user_id=CTX_USER_ID.get(),
        page=page,
        page_size=page_size,
        title=title,
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/answer/paper/get", summary="查看可答试卷详情")
async def get_answerable_exam_paper(paper_id: int = Query(..., description="试卷ID")):
    data = await exam_attempt_controller.get_answerable_paper(paper_id=paper_id, user_id=CTX_USER_ID.get())
    return Success(data=data)


@router.post("/attempt/start", summary="开始答题")
async def start_exam_attempt(payload: ExamAttemptStartPayload):
    data = await exam_attempt_controller.start_attempt(paper_id=payload.paper_id, user_id=CTX_USER_ID.get())
    return Success(data=data)


@router.post("/attempt/save", summary="暂存答卷")
async def save_exam_attempt(payload: ExamAttemptSavePayload):
    data = await exam_attempt_controller.save_attempt(obj_in=payload, user_id=CTX_USER_ID.get())
    return Success(data=data, msg="Saved Successfully")


@router.post("/attempt/submit", summary="提交答卷")
async def submit_exam_attempt(payload: ExamAttemptSubmitPayload):
    data = await exam_attempt_controller.submit_attempt(obj_in=payload, user_id=CTX_USER_ID.get())
    return Success(data=data, msg="Submitted Successfully")


@router.get("/attempt/my_list", summary="查看我的答卷列表")
async def list_my_exam_attempts(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    title: str | None = Query(None, description="试卷标题"),
):
    total, data = await exam_attempt_controller.list_my_attempts(
        user_id=CTX_USER_ID.get(),
        page=page,
        page_size=page_size,
        title=title,
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/attempt/my_get", summary="查看我的答卷详情")
async def get_my_exam_attempt(attempt_id: int = Query(..., description="答卷ID")):
    data = await exam_attempt_controller.get_my_attempt_detail(attempt_id=attempt_id, user_id=CTX_USER_ID.get())
    return Success(data=data)


@router.get("/practice/bank/list", summary="查看练习题库列表")
async def list_exam_practice_banks():
    data = await exam_practice_controller.list_practice_banks()
    return Success(data=data)


@router.get("/practice/question/list", summary="查看练习可选题目")
async def list_exam_practice_questions(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    bank_id: int | None = Query(None, description="题库ID"),
    question_type: str | None = Query(None, description="题型"),
    difficulty: str | None = Query(None, description="难度"),
    stem: str | None = Query(None, description="题干关键字"),
):
    total, data = await exam_practice_controller.list_practice_questions(
        page=page,
        page_size=page_size,
        bank_id=bank_id,
        question_type=question_type,
        difficulty=difficulty,
        stem=stem,
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/practice/start", summary="开始练习")
async def start_exam_practice(payload: ExamPracticeStartPayload):
    data = await exam_practice_controller.start_practice(obj_in=payload, user_id=CTX_USER_ID.get())
    return Success(data=data, msg="Practice Started")


@router.get("/practice/get", summary="查看练习详情")
async def get_exam_practice(session_id: int = Query(..., description="练习ID")):
    data = await exam_practice_controller.get_session_detail(session_id=session_id, user_id=CTX_USER_ID.get())
    return Success(data=data)


@router.get("/practice/my_list", summary="查看我的练习记录")
async def list_my_exam_practices(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
):
    total, data = await exam_practice_controller.list_my_sessions(
        user_id=CTX_USER_ID.get(),
        page=page,
        page_size=page_size,
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/practice/answer", summary="提交练习答案")
async def answer_exam_practice(payload: ExamPracticeAnswerPayload):
    data = await exam_practice_controller.submit_answer(obj_in=payload, user_id=CTX_USER_ID.get())
    return Success(data=data, msg="Answered Successfully")


@router.post("/practice/finish", summary="完成练习")
async def finish_exam_practice(payload: ExamPracticeActionPayload):
    data = await exam_practice_controller.finish_practice(obj_in=payload, user_id=CTX_USER_ID.get())
    return Success(data=data, msg="Practice Finished")


@router.post("/practice/retry", summary="重新练习")
async def retry_exam_practice(payload: ExamPracticeActionPayload):
    data = await exam_practice_controller.retry_practice(obj_in=payload, user_id=CTX_USER_ID.get())
    return Success(data=data, msg="Practice Retried")


@router.delete("/practice/delete", summary="删除练习记录")
async def delete_exam_practice(session_id: int = Query(..., description="练习ID")):
    await exam_practice_controller.delete_practice(session_id=session_id, user_id=CTX_USER_ID.get())
    return Success(msg="Deleted Successfully")


@router.get("/grading/list", summary="查看待阅卷列表")
async def list_exam_grading_tasks(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    paper_title: str | None = Query(None, description="试卷标题"),
    username: str | None = Query(None, description="答题人"),
    status: str | None = Query(None, description="状态"),
):
    total, data = await exam_grading_controller.list_grading_attempts(
        page=page,
        page_size=page_size,
        paper_title=paper_title,
        username=username,
        status=status,
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/grading/get", summary="查看阅卷详情")
async def get_exam_grading_detail(attempt_id: int = Query(..., description="答卷ID")):
    data = await exam_grading_controller.get_grading_detail(attempt_id=attempt_id)
    return Success(data=data)


@router.post("/grading/claim", summary="领取阅卷")
async def claim_exam_grading(payload: ExamGradingClaimPayload):
    data = await exam_grading_controller.claim_grading(obj_in=payload, reviewer_id=CTX_USER_ID.get())
    return Success(data=data, msg="Claimed Successfully")


@router.post("/grading/release", summary="释放阅卷")
async def release_exam_grading(payload: ExamGradingClaimPayload):
    data = await exam_grading_controller.release_grading(obj_in=payload, reviewer_id=CTX_USER_ID.get())
    return Success(data=data, msg="Released Successfully")


@router.post("/grading/score", summary="人工评分")
async def score_exam_answer(payload: ExamGradingScorePayload):
    await exam_grading_controller.score_answer(obj_in=payload, reviewer_id=CTX_USER_ID.get())
    return Success(msg="Scored Successfully")


@router.post("/grading/complete", summary="完成阅卷")
async def complete_exam_grading(payload: ExamGradingCompletePayload):
    await exam_grading_controller.complete_grading(obj_in=payload, reviewer_id=CTX_USER_ID.get())
    return Success(msg="Completed Successfully")

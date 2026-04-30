from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.core.ctx import CTX_USER_ID
from app.knowledge.constants import KnowledgeArticleStatus
from app.knowledge.controllers import knowledge_article_controller, knowledge_category_controller
from app.knowledge.schemas import (
    KnowledgeArticleCreate,
    KnowledgeArticleUpdate,
    KnowledgeCategoryCreate,
    KnowledgeCategoryUpdate,
)
from app.schemas.base import Success, SuccessExtra

router = APIRouter()


@router.get("/category/list", summary="查看知识分类列表")
async def list_knowledge_category():
    data = await knowledge_category_controller.get_category_tree()
    return Success(data=data)


@router.get("/category/get", summary="查看知识分类")
async def get_knowledge_category(
    id: int = Query(..., description="分类ID"),
):
    category = await knowledge_category_controller.get(id=id)
    data = await category.to_dict()
    return Success(data=data)


@router.post("/category/create", summary="创建知识分类")
async def create_knowledge_category(
    category_in: KnowledgeCategoryCreate,
):
    await knowledge_category_controller.create_category(obj_in=category_in)
    return Success(msg="Created Successfully")


@router.post("/category/update", summary="更新知识分类")
async def update_knowledge_category(
    category_in: KnowledgeCategoryUpdate,
):
    await knowledge_category_controller.update_category(obj_in=category_in)
    return Success(msg="Updated Successfully")


@router.delete("/category/delete", summary="删除知识分类")
async def delete_knowledge_category(
    category_id: int = Query(..., description="分类ID"),
):
    await knowledge_category_controller.delete_category(category_id=category_id)
    return Success(msg="Deleted Successfully")


@router.get("/article/list", summary="查看知识文章列表")
async def list_knowledge_article(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    title: str | None = Query(None, description="文章标题"),
    category_id: int | None = Query(None, description="分类ID"),
    status: KnowledgeArticleStatus | None = Query(None, description="文章状态"),
    is_top: bool | None = Query(None, description="是否置顶"),
):
    total, data = await knowledge_article_controller.list_articles(
        page=page,
        page_size=page_size,
        title=title,
        category_id=category_id,
        status=status,
        is_top=is_top,
        user_id=CTX_USER_ID.get(),
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/article/get", summary="查看知识文章")
async def get_knowledge_article(
    article_id: int = Query(..., description="文章ID"),
):
    data = await knowledge_article_controller.get_article_detail(
        article_id=article_id,
        user_id=CTX_USER_ID.get(),
    )
    return Success(data=data)


@router.get("/published/category/list", summary="查看已发布知识分类列表")
async def list_published_knowledge_category():
    data = await knowledge_category_controller.get_published_category_tree()
    return Success(data=data)


@router.get("/published/article/list", summary="查看已发布知识文章列表")
async def list_published_knowledge_article(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    title: str | None = Query(None, description="文章标题"),
    category_id: int | None = Query(None, description="分类ID"),
):
    total, data = await knowledge_article_controller.list_articles(
        page=page,
        page_size=page_size,
        title=title,
        category_id=category_id,
        status=KnowledgeArticleStatus.PUBLISHED,
        active_only=True,
    )
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/published/article/get", summary="查看已发布知识文章")
async def get_published_knowledge_article(
    article_id: int = Query(..., description="文章ID"),
):
    data = await knowledge_article_controller.get_article_detail(
        article_id=article_id,
        status=KnowledgeArticleStatus.PUBLISHED,
        active_only=True,
    )
    return Success(data=data)


@router.post("/article/block/upload", summary="上传知识文章内容文件")
async def upload_knowledge_article_block(
    file: UploadFile = File(..., description="知识文件"),
):
    data = await knowledge_article_controller.upload_article_block(file=file)
    return Success(data=data)


@router.get("/article/block/file", summary="查看知识文章内容文件")
async def get_knowledge_article_block_file(
    block_id: int | None = Query(None, description="内容块ID"),
    temp_token: str | None = Query(None, description="临时上传令牌"),
):
    data = await knowledge_article_controller.get_block_file(
        block_id=block_id,
        temp_token=temp_token,
        user_id=CTX_USER_ID.get(),
    )
    return FileResponse(data["path"], media_type=data["mime_type"], filename=data["file_name"])


@router.get("/published/article/block/file", summary="查看已发布知识文章内容文件")
async def get_published_knowledge_article_block_file(
    block_id: int = Query(..., description="内容块ID"),
):
    data = await knowledge_article_controller.get_block_file(
        block_id=block_id,
        status=KnowledgeArticleStatus.PUBLISHED,
        active_only=True,
    )
    return FileResponse(data["path"], media_type=data["mime_type"], filename=data["file_name"])


@router.post("/article/create", summary="创建知识文章")
async def create_knowledge_article(
    article_in: KnowledgeArticleCreate,
):
    await knowledge_article_controller.create_article(obj_in=article_in, user_id=CTX_USER_ID.get())
    return Success(msg="Created Successfully")


@router.post("/article/update", summary="更新知识文章")
async def update_knowledge_article(
    article_in: KnowledgeArticleUpdate,
):
    await knowledge_article_controller.update_article(obj_in=article_in, user_id=CTX_USER_ID.get())
    return Success(msg="Updated Successfully")


@router.delete("/article/delete", summary="删除知识文章")
async def delete_knowledge_article(
    article_id: int = Query(..., description="文章ID"),
):
    await knowledge_article_controller.delete_article(article_id=article_id, user_id=CTX_USER_ID.get())
    return Success(msg="Deleted Successfully")

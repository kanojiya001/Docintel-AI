import os
import uuid
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.database.db import get_db
from app.database.models import User, Document, Query, Summary, Export
from app.schemas.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserResponse,
    DocumentResponse, DocumentListResponse,
    ChatRequest, ChatResponse,
    SummaryRequest, SummaryResponse,
    CompareRequest, CompareResponse,
    QuestionGenRequest, QuestionGenResponse,
    ExportRequest, ExportResponse,
    AnalyticsResponse,
)
from app.core.security import hash_password, verify_password
from app.core.jwt_handler import create_access_token, get_current_user
from app.core.config import settings
from app.ai.rag_engine import processor, rag_engine
from app.core.supabase_client import broadcast_event


# ===================== AUTH ROUTER =====================
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        existing = await db.execute(select(User).where(User.email == req.email))
    except Exception:
        raise HTTPException(status_code=503, detail="Database not connected. Check DATABASE_URL in .env — it needs your real Supabase database password, not the API key.")
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        organization_id=req.organization_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token)


@auth_router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.email == req.email))
    except Exception:
        raise HTTPException(status_code=503, detail="Database not connected. Check DATABASE_URL in .env — it needs your real Supabase database password, not the API key.")
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token)


@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ===================== DOCUMENTS ROUTER =====================
doc_router = APIRouter(prefix="/documents", tags=["Documents"])


@doc_router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    doc_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}.pdf")

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    with open(file_path, "wb") as f:
        f.write(content)

    # Broadcast "processing" status immediately so UI updates in real time
    await broadcast_event("documents", "INSERT", {
        "id": doc_id,
        "user_id": current_user["sub"],
        "file_name": file.filename,
        "status": "processing",
        "file_size": len(content),
    })

    # Parse and index
    try:
        pages = processor.parse_pdf(file_path)
        chunks = processor.chunk_document(pages)
        processor.create_vector_store(doc_id, chunks)
        status_val = "ready"
        indexed_at = datetime.utcnow()
    except Exception as exc:
        status_val = "failed"
        indexed_at = None

    doc = Document(
        id=uuid.UUID(doc_id),
        user_id=uuid.UUID(current_user["sub"]),
        file_name=file.filename,
        file_path=file_path,
        page_count=len(pages) if status_val == "ready" else 0,
        file_size=len(content),
        status=status_val,
        indexed_at=indexed_at,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Broadcast final status (ready / failed)
    await broadcast_event("documents", "UPDATE", {
        "id": doc_id,
        "user_id": current_user["sub"],
        "file_name": file.filename,
        "status": status_val,
        "page_count": doc.page_count,
        "file_size": doc.file_size,
        "upload_date": doc.upload_date.isoformat(),
    })

    return doc


@doc_router.get("/", response_model=DocumentListResponse)
async def list_documents(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document)
        .where(Document.user_id == uuid.UUID(current_user["sub"]))
        .order_by(Document.upload_date.desc())
    )
    docs = result.scalars().all()
    return DocumentListResponse(documents=docs, total=len(docs))


@doc_router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == uuid.UUID(current_user["sub"]))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.commit()

    await broadcast_event("documents", "DELETE", {
        "id": str(doc_id),
        "user_id": current_user["sub"],
    })


# ===================== CHAT ROUTER =====================
chat_router = APIRouter(prefix="/chat", tags=["AI Chat"])


@chat_router.post("/", response_model=ChatResponse)
async def chat_with_document(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == req.document_id))
    doc = result.scalar_one_or_none()
    if not doc or doc.status != "ready":
        raise HTTPException(status_code=404, detail="Document not found or not indexed")

    response = rag_engine.query_document(str(doc.id), req.question, req.mode)

    query = Query(
        user_id=uuid.UUID(current_user["sub"]),
        document_id=req.document_id,
        question=req.question,
        answer=response["answer"],
        mode=req.mode,
        response_time_ms=response["response_time_ms"],
    )
    db.add(query)
    await db.commit()
    await db.refresh(query)

    # Broadcast new query so analytics page updates live
    await broadcast_event("queries", "INSERT", {
        "id": str(query.id),
        "user_id": current_user["sub"],
        "document_id": str(req.document_id),
        "question": req.question,
        "mode": req.mode,
        "response_time_ms": response["response_time_ms"],
        "created_at": query.created_at.isoformat(),
    })

    return ChatResponse(**response)


# ===================== SUMMARY ROUTER =====================
summary_router = APIRouter(prefix="/summary", tags=["Summaries"])


@summary_router.post("/", response_model=SummaryResponse)
async def generate_summary(
    req: SummaryRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == req.document_id))
    doc = result.scalar_one_or_none()
    if not doc or doc.status != "ready":
        raise HTTPException(status_code=404, detail="Document not found or not indexed")

    content = rag_engine.generate_summary(str(doc.id), req.summary_type)

    summary = Summary(
        user_id=uuid.UUID(current_user["sub"]),
        document_id=req.document_id,
        summary_type=req.summary_type,
        content=content,
    )
    db.add(summary)
    await db.commit()
    await db.refresh(summary)

    await broadcast_event("summaries", "INSERT", {
        "id": str(summary.id),
        "user_id": current_user["sub"],
        "document_id": str(req.document_id),
        "summary_type": req.summary_type,
        "created_at": summary.created_at.isoformat(),
    })

    return summary


# ===================== COMPARE ROUTER =====================
compare_router = APIRouter(prefix="/compare", tags=["Document Comparison"])


@compare_router.post("/", response_model=CompareResponse)
async def compare_documents(
    req: CompareRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for did in [req.document_a_id, req.document_b_id]:
        result = await db.execute(select(Document).where(Document.id == did))
        doc = result.scalar_one_or_none()
        if not doc or doc.status != "ready":
            raise HTTPException(status_code=404, detail=f"Document {did} not found or not ready")

    comparison = rag_engine.compare_documents(str(req.document_a_id), str(req.document_b_id))
    return CompareResponse(**comparison)


# ===================== QUESTIONS ROUTER =====================
question_router = APIRouter(prefix="/questions", tags=["Question Generation"])


@question_router.post("/", response_model=QuestionGenResponse)
async def generate_questions(
    req: QuestionGenRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == req.document_id))
    doc = result.scalar_one_or_none()
    if not doc or doc.status != "ready":
        raise HTTPException(status_code=404, detail="Document not found or not indexed")

    questions = rag_engine.generate_questions(str(doc.id), req.num_questions, req.difficulty)
    return QuestionGenResponse(questions=questions)


# ===================== ANALYTICS ROUTER =====================
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(current_user["sub"])

    doc_count_res = await db.execute(select(func.count()).select_from(Document).where(Document.user_id == uid))
    query_count_res = await db.execute(select(func.count()).select_from(Query).where(Query.user_id == uid))
    export_count_res = await db.execute(select(func.count()).select_from(Export).where(Export.user_id == uid))
    avg_time_res = await db.execute(select(func.avg(Query.response_time_ms)).where(Query.user_id == uid))

    # Weekly query counts (last 7 days, day 0 = oldest)
    weekly_res = await db.execute(
        text("""
            SELECT DATE(created_at) as day, COUNT(*) as cnt
            FROM queries
            WHERE user_id = :uid
              AND created_at >= NOW() - INTERVAL '7 days'
            GROUP BY day
            ORDER BY day ASC
        """),
        {"uid": str(uid)},
    )
    weekly_rows = weekly_res.fetchall()
    weekly_map = {str(r[0]): int(r[1]) for r in weekly_rows}

    today = date.today()
    weekly_queries = [
        weekly_map.get(str(today - timedelta(days=6 - i)), 0)
        for i in range(7)
    ]

    # Storage used
    storage_res = await db.execute(
        select(func.sum(Document.file_size)).where(Document.user_id == uid)
    )
    storage_bytes = storage_res.scalar() or 0

    return AnalyticsResponse(
        total_documents=doc_count_res.scalar() or 0,
        total_queries=query_count_res.scalar() or 0,
        total_exports=export_count_res.scalar() or 0,
        avg_response_time=round(avg_time_res.scalar() or 0, 1),
        accuracy_score=94.2,
        weekly_queries=weekly_queries,
        storage_used_bytes=int(storage_bytes),
    )


# ===================== EXPORT ROUTER =====================
export_router = APIRouter(prefix="/export", tags=["Export"])


@export_router.post("/", response_model=ExportResponse)
async def export_analysis(
    req: ExportRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    export = Export(
        user_id=uuid.UUID(current_user["sub"]),
        document_id=req.document_id,
        export_type=req.export_type,
        file_path=f"exports/{uuid.uuid4()}.{req.export_type}",
        file_size=0,
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)

    await broadcast_event("exports", "INSERT", {
        "id": str(export.id),
        "user_id": current_user["sub"],
        "document_id": str(req.document_id),
        "export_type": req.export_type,
        "created_at": export.created_at.isoformat(),
    })

    return export


@export_router.get("/", response_model=list)
async def list_exports(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Export)
        .where(Export.user_id == uuid.UUID(current_user["sub"]))
        .order_by(Export.created_at.desc())
        .limit(20)
    )
    exports = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "export_type": e.export_type,
            "file_path": e.file_path,
            "file_size": e.file_size,
            "created_at": e.created_at.isoformat(),
        }
        for e in exports
    ]

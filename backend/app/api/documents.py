import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentResponse
from app.services.rag.parser import parse_markdown, parse_pdf_bytes
from app.services.rag.chunker import chunk_markdown, chunk_plain_text
from app.services.rag.embedder import embedder
from app.services.rag.vector_store import insert_chunks
from app.config import settings

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    authorship: str = Form("unknown"),
    title: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    # Validate file type
    content_type = file.content_type or ""
    if "pdf" in content_type:
        content_type = "application/pdf"
    elif "markdown" in content_type or file.filename.endswith(".md"):
        content_type = "text/markdown"
    else:
        raise HTTPException(status_code=400, detail="Only PDF and Markdown files are supported")

    # Read file
    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_size_mb}MB limit")

    # Parse
    if content_type == "text/markdown":
        raw_text = parse_markdown(content)
        chunks = chunk_markdown(raw_text)
    else:
        raw_text = parse_pdf_bytes(content)
        chunks = chunk_plain_text(raw_text)

    if not chunks:
        raise HTTPException(status_code=400, detail="No content could be extracted from the file")

    # Create document record
    doc = Document(
        filename=file.filename,
        content_type=content_type,
        source_type="upload",
        authorship=authorship,
        title=title or file.filename,
        raw_text=raw_text,
        char_count=len(raw_text),
        processing_status="processing",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Generate embeddings
    texts = [chunk["content"] for chunk in chunks]
    embeddings = embedder.encode(texts)

    # Store chunks
    await insert_chunks(db, str(doc.id), chunks, embeddings.tolist())

    # Update document status
    doc.processing_status = "ready"
    doc.chunk_count = len(chunks)
    await db.flush()
    await db.refresh(doc)

    return doc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return result.scalars().all()


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(doc)
    await db.flush()

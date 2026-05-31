import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, async_session_factory
from app.models.document import Document, DocumentChunk
from app.models.knowledge import KnowledgeNode, KnowledgeEdge
from app.schemas.document import DocumentResponse, DocumentChunkResponse, DocumentListResponse
from app.schemas.knowledge import KnowledgeGraphResponse, KnowledgeNodeResponse, KnowledgeEdgeResponse
from app.services.rag.parser import parse_markdown, parse_pdf_bytes
from app.services.rag.chunker import chunk_markdown, chunk_plain_text
from app.services.rag.embedder import embedder
from app.services.rag.vector_store import insert_chunks
from app.services.document.knowledge_extractor import extract_knowledge_from_document
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


async def _extract_knowledge_background(
    document_id: str,
    title: str,
    content_type: str,
    chunks: list[dict],
):
    """Background task: extract knowledge from document chunks."""
    async with async_session_factory() as session:
        try:
            # Mark knowledge extraction as in progress (flush, not commit —
            # same transaction as extraction below)
            await session.execute(
                text("""
                    UPDATE documents
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{knowledge_status}',
                        '"processing"'
                    )
                    WHERE id = :id
                """),
                {"id": document_id},
            )

            await extract_knowledge_from_document(
                session, document_id, title, content_type, chunks,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Background knowledge extraction failed for document %s", document_id)
            # Best-effort: mark failed in a separate transaction
            try:
                async with async_session_factory() as err_session:
                    await err_session.execute(
                        text("""
                            UPDATE documents
                            SET metadata = jsonb_set(
                                COALESCE(metadata, '{}'::jsonb),
                                '{knowledge_status}',
                                '"failed"'
                            ),
                            error_message = 'Knowledge extraction failed'
                            WHERE id = :id
                        """),
                        {"id": document_id},
                    )
                    await err_session.commit()
            except Exception:
                logger.exception("Failed to update knowledge_status to failed for document %s", document_id)


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
    elif "markdown" in content_type or (file.filename and file.filename.endswith(".md")):
        content_type = "text/markdown"
    else:
        raise HTTPException(status_code=400, detail="Only PDF and Markdown files are supported")

    # Read file
    content = await file.read()
    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_size_mb}MB limit")

    # Parse
    try:
        if content_type == "text/markdown":
            raw_text = parse_markdown(content)
            chunks = chunk_markdown(raw_text)
        else:
            raw_text = parse_pdf_bytes(content)
            chunks = chunk_plain_text(raw_text)
    except Exception:
        logger.exception("Failed to parse document %s", file.filename)
        raise HTTPException(status_code=400, detail="Failed to parse file content")

    if not chunks:
        raise HTTPException(status_code=400, detail="No content could be extracted from the file")

    # Create document record
    doc_title = title or file.filename or "untitled"
    doc = Document(
        filename=file.filename or "untitled",
        content_type=content_type,
        source_type="upload",
        authorship=authorship,
        title=doc_title,
        raw_text=raw_text,
        char_count=len(raw_text),
        processing_status="processing",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    try:
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
    except Exception:
        doc.processing_status = "failed"
        doc.error_message = "Failed during chunking or embedding"
        await db.flush()
        logger.exception("Failed to process document %s", doc.id)
        raise HTTPException(status_code=500, detail="Failed to process document")

    # Start background knowledge extraction
    asyncio.create_task(_extract_knowledge_background(str(doc.id), doc_title, content_type, chunks))

    return doc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    # Total count
    count_result = await db.execute(select(func.count(Document.id)))
    total = count_result.scalar() or 0

    # Paginated query
    offset = (page - 1) * size
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).offset(offset).limit(size)
    )
    items = result.scalars().all()

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{doc_id}/chunks", response_model=list[DocumentChunkResponse])
async def get_document_chunks(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Verify document exists
    doc_result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return result.scalars().all()


@router.get("/{doc_id}/knowledge", response_model=KnowledgeGraphResponse)
async def get_document_knowledge(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # Find knowledge nodes that reference this document
    result = await db.execute(
        text("""
            SELECT id, label, node_type, description, confidence
            FROM knowledge_nodes
            WHERE :doc_id = ANY(source_ids)
            ORDER BY label
        """),
        {"doc_id": doc_id},
    )
    node_rows = result.all()

    if not node_rows:
        return KnowledgeGraphResponse(nodes=[], edges=[])

    node_ids = [row[0] for row in node_rows]
    nodes = [
        KnowledgeNodeResponse(
            id=row[0], label=row[1], node_type=row[2],
            description=row[3], confidence=row[4],
        )
        for row in node_rows
    ]

    # Get edges between these nodes
    edge_result = await db.execute(
        text("""
            SELECT id, source_node_id, target_node_id, relation_type, weight, evidence
            FROM knowledge_edges
            WHERE source_node_id = ANY(:node_ids)
               OR target_node_id = ANY(:node_ids)
            ORDER BY weight DESC
        """),
        {"node_ids": node_ids},
    )
    edge_rows = edge_result.all()
    edges = [
        KnowledgeEdgeResponse(
            id=row[0], source_node_id=row[1], target_node_id=row[2],
            relation_type=row[3], weight=row[4], evidence=row[5],
        )
        for row in edge_rows
    ]

    return KnowledgeGraphResponse(nodes=nodes, edges=edges)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove document reference from knowledge nodes
    nodes_result = await db.execute(
        text("SELECT id, source_ids FROM knowledge_nodes WHERE :doc_id = ANY(source_ids)"),
        {"doc_id": doc_id},
    )
    affected_nodes = nodes_result.all()
    for row in affected_nodes:
        node_id = row[0]
        remaining = [sid for sid in (row[1] or []) if str(sid) != str(doc_id)]
        if not remaining:
            # No more sources → delete node (edges cascade)
            await db.execute(text("DELETE FROM knowledge_nodes WHERE id = :id"), {"id": node_id})
        else:
            await db.execute(
                text("UPDATE knowledge_nodes SET source_ids = :ids WHERE id = :id"),
                {"id": node_id, "ids": remaining},
            )

    await db.delete(doc)
    await db.flush()

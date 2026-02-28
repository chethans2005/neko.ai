"""
API Routes - FastAPI Route Definitions

All API endpoints for the AI Presentation Generator.
"""
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
import os
from datetime import datetime
import shutil

from app.models.schemas import (
    StartSessionRequest, GenerateRequest, UpdateSlideRequest, RollbackSlideRequest,
    SessionResponse, GenerateResponse, JobStatusResponse, PreviewResponse,
    UpdateSlideResponse, DownloadResponse, ErrorResponse, TemplateType,
    SlideWithHistory, SlideVersion, JobStatus,
    SignupRequest, LoginRequest, GoogleLoginRequest, AuthResponse,
    AuthUserResponse, HistoryItemResponse,
)
from app.services.session_service import session_manager
from app.services.outline_service import outline_service
from app.services.slide_service import slide_service
from app.services.ppt_service import ppt_service
from app.services.template_service import template_service
from app.services.job_service import job_manager
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    verify_google_id_token,
    link_history_to_session,
)
from app.ai.router import ai_router
from app.api.dependencies import require_user, ensure_session_owned_by_user
from db.database import get_db_session
from db import crud

router = APIRouter()
SLIDES_GENERATION_LIMIT = 50


# =============================================================================
# Auth Endpoints
# =============================================================================

@router.post("/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    db = await get_db_session()
    try:
        existing = await crud.get_user_by_email(db, request.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email is already registered")

        user = await crud.create_user(
            db=db,
            name=request.name.strip(),
            email=request.email,
            password_hash=hash_password(request.password),
            provider="email",
        )
        token = create_access_token(user.user_id, user.email, user.name)
        return AuthResponse(
            access_token=token,
            user=AuthUserResponse(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
                avatar_url=user.avatar_url,
                requests_generated=user.requests_generated,
            ),
        )
    finally:
        await db.close()


@router.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    db = await get_db_session()
    try:
        user = await crud.get_user_by_email(db, request.email)
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        await crud.update_user_login(db, user)
        token = create_access_token(user.user_id, user.email, user.name)
        return AuthResponse(
            access_token=token,
            user=AuthUserResponse(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
                avatar_url=user.avatar_url,
                requests_generated=user.requests_generated,
            ),
        )
    finally:
        await db.close()


@router.post("/auth/google", response_model=AuthResponse)
async def login_google(request: GoogleLoginRequest):
    try:
        email, name, sub, picture = await verify_google_id_token(request.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db = await get_db_session()
    try:
        user = await crud.get_user_by_google_sub(db, sub)
        if not user:
            user = await crud.get_user_by_email(db, email)
            if user:
                user.google_sub = sub
                user.provider = "google"
                user.avatar_url = picture
                await db.commit()
                await db.refresh(user)
            else:
                user = await crud.create_user(
                    db=db,
                    name=name,
                    email=email,
                    provider="google",
                    google_sub=sub,
                    avatar_url=picture,
                )
        elif picture and user.avatar_url != picture:
            user.avatar_url = picture
            await db.commit()
            await db.refresh(user)

        await crud.update_user_login(db, user)
        token = create_access_token(user.user_id, user.email, user.name)
        return AuthResponse(
            access_token=token,
            user=AuthUserResponse(
                user_id=user.user_id,
                name=user.name,
                email=user.email,
                avatar_url=user.avatar_url,
                requests_generated=user.requests_generated,
            ),
        )
    finally:
        await db.close()


@router.get("/auth/me", response_model=AuthUserResponse)
async def auth_me(authorization: Optional[str] = Header(default=None)):
    user = await require_user(authorization)
    return AuthUserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        avatar_url=user.avatar_url,
        requests_generated=user.requests_generated,
    )


@router.get("/history")
async def get_user_history(authorization: Optional[str] = Header(default=None)):
    user = await require_user(authorization)
    db = await get_db_session()
    try:
        history = await crud.get_user_history(db, user.id)
        return {
            "items": [
                HistoryItemResponse(
                    history_id=item.history_id,
                    session_id=item.session_uuid,
                    topic=item.topic,
                    filename=item.filename,
                    slide_count=item.slide_count,
                    created_at=item.created_at,
                ).model_dump()
                for item in history
            ]
        }
    finally:
        await db.close()


@router.get("/history/download/{history_id}")
async def download_from_history(history_id: str, authorization: Optional[str] = Header(default=None)):
    user = await require_user(authorization)
    db = await get_db_session()
    try:
        item = await crud.get_history_by_id(db, history_id)
        if not item or item.user_id != user.id:
            raise HTTPException(status_code=404, detail="History item not found")

        if not os.path.exists(item.file_path):
            raise HTTPException(status_code=404, detail="Presentation file no longer exists")

        return FileResponse(
            path=item.file_path,
            filename=item.filename,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    finally:
        await db.close()


@router.delete("/history/{history_id}")
async def delete_history_item(history_id: str, authorization: Optional[str] = Header(default=None)):
    user = await require_user(authorization)
    db = await get_db_session()
    try:
        item = await crud.get_history_by_id(db, history_id)
        if not item or item.user_id != user.id:
            raise HTTPException(status_code=404, detail="History item not found")

        file_path = item.file_path
        await crud.delete_history_item(db, item)

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                output_dir = os.path.dirname(file_path)
                if output_dir and os.path.isdir(output_dir) and not os.listdir(output_dir):
                    shutil.rmtree(output_dir, ignore_errors=True)
            except OSError:
                pass

        return {"success": True, "message": "History item deleted"}
    finally:
        await db.close()


# =============================================================================
# Session Endpoints
# =============================================================================

@router.post("/session/start", response_model=SessionResponse)
async def start_session(request: StartSessionRequest, authorization: Optional[str] = Header(default=None)):
    """
    Start a new presentation session.
    
    Creates a new session with the specified template and tone.
    Returns session_id to use for subsequent requests.
    """
    try:
        user = await require_user(authorization)
        session = await session_manager.create_session(
            template=request.template,
            tone=request.tone
        )

        db = await get_db_session()
        try:
            await crud.map_session_to_user(db, user.id, session.session_id)
        finally:
            await db.close()
        
        return SessionResponse(
            session_id=session.session_id,
            template=session.template,
            tone=session.tone,
            created_at=session.created_at,
            message="Session created successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(session_id: str, authorization: Optional[str] = Header(default=None)):
    """Get session details."""
    user = await require_user(authorization)
    await ensure_session_owned_by_user(session_id, user.id)

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.session_id,
        "topic": session.topic,
        "template": session.template.value,
        "tone": session.tone.value,
        "slides_count": len(session.slides),
        "created_at": session.created_at.isoformat(),
        "last_updated": session.last_updated.isoformat()
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, authorization: Optional[str] = Header(default=None)):
    """Delete a session."""
    user = await require_user(authorization)
    await ensure_session_owned_by_user(session_id, user.id)

    deleted = await session_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}


# =============================================================================
# Generation Endpoints
# =============================================================================

async def _generate_presentation_task(
    session_id: str,
    topic: str,
    num_slides: int,
    additional_context: Optional[str],
    job_id: str
):
    """Background task for generating a presentation."""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found")
        
        job_manager.update_job_progress(job_id, 10, "Generating outline...")
        
        # Generate slides
        slides = await outline_service.generate_outline(
            topic=topic,
            num_slides=num_slides,
            tone=session.tone,
            context=session.context_memory if session.context_memory else None,
            additional_instructions=additional_context
        )
        
        job_manager.update_job_progress(job_id, 70, "Building presentation...")
        
        # Update session
        await session_manager.update_session(
            session_id=session_id,
            topic=topic,
            slides=slides,
            context_memory=f"Created presentation about {topic} with {len(slides)} slides"
        )
        
        # Add to chat history
        await session_manager.add_chat_message(
            session_id=session_id,
            role="user",
            content=f"Create a presentation about: {topic}"
        )
        
        await session_manager.add_chat_message(
            session_id=session_id,
            role="assistant",
            content=f"Created {len(slides)} slides about {topic}"
        )
        
        job_manager.update_job_progress(job_id, 90, "Finalizing...")
        
        # Generate PPT file
        updated_session = await session_manager.get_session(session_id)
        filepath = ppt_service.create_presentation(updated_session)
        await link_history_to_session(
            session_uuid=session_id,
            topic=topic,
            filepath=filepath,
            slide_count=len(slides),
        )
        
        job_manager.update_job_progress(job_id, 100, "Complete!")
        
        return {"slides_count": len(slides), "topic": topic}
        
    except Exception as e:
        raise Exception(f"Failed to generate presentation: {str(e)}")


@router.post("/generate", response_model=GenerateResponse)
async def generate_presentation(request: GenerateRequest, authorization: Optional[str] = Header(default=None)):
    """
    Generate a new presentation (async).
    
    Queues a background job and returns immediately with a job_id.
    Poll /status/{job_id} to check progress.
    """
    user = await require_user(authorization)
    projected_total_slides = (user.requests_generated or 0) + max(1, request.num_slides)
    if projected_total_slides > SLIDES_GENERATION_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=f"Slide generation limit reached ({SLIDES_GENERATION_LIMIT} total slides).",
        )
    await ensure_session_owned_by_user(request.session_id, user.id)

    session = await session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        job = await job_manager.create_job(
            session_id=request.session_id,
            job_type="generate",
            task_func=_generate_presentation_task,
            topic=request.topic,
            num_slides=request.num_slides,
            additional_context=request.additional_context
        )
        
        return GenerateResponse(
            job_id=job.job_id,
            session_id=request.session_id,
            status=job.status,
            message="Generation started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-sync")
async def generate_presentation_sync(request: GenerateRequest, authorization: Optional[str] = Header(default=None)):
    """
    Generate a new presentation (synchronous).
    
    Waits for generation to complete before returning.
    Use for simpler integrations.
    """
    user = await require_user(authorization)
    projected_total_slides = (user.requests_generated or 0) + max(1, request.num_slides)
    if projected_total_slides > SLIDES_GENERATION_LIMIT:
        raise HTTPException(
            status_code=403,
            detail=f"Slide generation limit reached ({SLIDES_GENERATION_LIMIT} total slides).",
        )
    await ensure_session_owned_by_user(request.session_id, user.id)

    session = await session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Generate slides
        slides = await outline_service.generate_outline(
            topic=request.topic,
            num_slides=request.num_slides,
            tone=session.tone,
            context=session.context_memory if session.context_memory else None,
            additional_instructions=request.additional_context
        )
        
        # Update session
        await session_manager.update_session(
            session_id=request.session_id,
            topic=request.topic,
            slides=slides,
            context_memory=f"Created presentation about {request.topic} with {len(slides)} slides"
        )
        
        # Add to chat history
        await session_manager.add_chat_message(
            session_id=request.session_id,
            role="user",
            content=f"Create a presentation about: {request.topic}"
        )
        
        await session_manager.add_chat_message(
            session_id=request.session_id,
            role="assistant",
            content=f"Created {len(slides)} slides about {request.topic}"
        )
        
        # Generate PPT file
        updated_session = await session_manager.get_session(request.session_id)
        filepath = ppt_service.create_presentation(updated_session)
        await link_history_to_session(
            session_uuid=request.session_id,
            topic=request.topic,
            filepath=filepath,
            slide_count=len(slides),
        )
        
        return {
            "success": True,
            "session_id": request.session_id,
            "topic": request.topic,
            "slides_count": len(slides),
            "message": "Presentation generated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Status Endpoints
# =============================================================================

@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a generation job.
    
    Poll this endpoint to track progress of async generation.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        error=job.error
    )


# =============================================================================
# Preview Endpoints
# =============================================================================

@router.get("/preview/{session_id}", response_model=PreviewResponse)
async def preview_presentation(session_id: str, authorization: Optional[str] = Header(default=None)):
    """
    Get presentation preview for a session.
    
    Returns all slides with their current content for display.
    """
    user = await require_user(authorization)
    await ensure_session_owned_by_user(session_id, user.id)

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.slides:
        raise HTTPException(status_code=400, detail="No slides generated yet")
    
    return PreviewResponse(
        session_id=session.session_id,
        topic=session.topic or "",
        template=session.template,
        tone=session.tone,
        slides=session.slides,
        total_slides=len(session.slides),
        last_updated=session.last_updated
    )


# =============================================================================
# Slide Update Endpoints
# =============================================================================

@router.post("/update-slide", response_model=UpdateSlideResponse)
async def update_slide(request: UpdateSlideRequest, authorization: Optional[str] = Header(default=None)):
    """
    Update a specific slide using natural language.
    
    Only regenerates the specified slide, not the entire presentation.
    """
    try:
        user = await require_user(authorization)
        await ensure_session_owned_by_user(request.session_id, user.id)

        updated_slide = await slide_service.update_slide(
            session_id=request.session_id,
            slide_number=request.slide_number,
            instruction=request.instruction
        )
        
        if not updated_slide:
            raise HTTPException(status_code=404, detail="Slide not found")
        
        # Regenerate PPT file with updated slide
        session = await session_manager.get_session(request.session_id)
        if session:
            ppt_service.create_presentation(session)
        
        return UpdateSlideResponse(
            success=True,
            slide_number=request.slide_number,
            updated_slide=updated_slide,
            message=f"Slide {request.slide_number} updated successfully"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback-slide")
async def rollback_slide(request: RollbackSlideRequest, authorization: Optional[str] = Header(default=None)):
    """
    Rollback a slide to a previous version.
    """
    try:
        user = await require_user(authorization)
        await ensure_session_owned_by_user(request.session_id, user.id)

        slide = await slide_service.rollback_slide(
            session_id=request.session_id,
            slide_number=request.slide_number,
            version_index=request.version_index
        )
        
        if not slide:
            raise HTTPException(status_code=404, detail="Slide or version not found")
        
        # Regenerate PPT file
        session = await session_manager.get_session(request.session_id)
        if session:
            ppt_service.create_presentation(session)
        
        return {
            "success": True,
            "slide_number": request.slide_number,
            "current_version": slide.current_version,
            "message": f"Rolled back to version {request.version_index}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slide-history/{session_id}/{slide_number}")
async def get_slide_history(session_id: str, slide_number: int, authorization: Optional[str] = Header(default=None)):
    """
    Get version history for a specific slide.
    """
    user = await require_user(authorization)
    await ensure_session_owned_by_user(session_id, user.id)

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    slide_idx = slide_number - 1
    if slide_idx < 0 or slide_idx >= len(session.slides):
        raise HTTPException(status_code=404, detail="Slide not found")
    
    slide = session.slides[slide_idx]
    
    return {
        "slide_number": slide_number,
        "current_version": slide.current_version,
        "total_versions": len(slide.versions),
        "versions": [
            {
                "version": v.version,
                "title": v.title,
                "content": v.content,
                "instruction": v.instruction,
                "created_at": v.created_at.isoformat()
            }
            for v in slide.versions
        ]
    }


# =============================================================================
# Download Endpoints
# =============================================================================

@router.get("/download/{session_id}")
async def download_presentation(session_id: str, authorization: Optional[str] = Header(default=None)):
    """
    Download the generated PowerPoint file.
    """
    user = await require_user(authorization)
    await ensure_session_owned_by_user(session_id, user.id)

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not session.slides:
        raise HTTPException(status_code=400, detail="No presentation generated yet")
    
    # Generate fresh PPT file
    filepath = ppt_service.create_presentation(session)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="Failed to generate file")
    
    filename = os.path.basename(filepath)
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


# =============================================================================
# Template Endpoints
# =============================================================================

@router.get("/templates")
async def list_templates():
    """
    List available presentation templates.
    """
    return {
        "templates": template_service.list_templates()
    }


@router.post("/session/{session_id}/template")
async def update_session_template(session_id: str, template: TemplateType, authorization: Optional[str] = Header(default=None)):
    """
    Update the template for a session.
    """
    user = await require_user(authorization)
    await ensure_session_owned_by_user(session_id, user.id)

    session = await session_manager.update_session(
        session_id=session_id,
        template=template
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "template": template.value,
        "message": "Template updated"
    }


# =============================================================================
# AI Provider Status
# =============================================================================

@router.get("/ai/status")
async def get_ai_status():
    """
    Get status of AI providers.
    """
    return ai_router.get_status()


# =============================================================================
# Chat History
# =============================================================================

@router.get("/chat/{session_id}")
async def get_chat_history(session_id: str, authorization: Optional[str] = Header(default=None)):
    """
    Get chat history for a session.
    """
    user = await require_user(authorization)
    await ensure_session_owned_by_user(session_id, user.id)

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "related_slide": msg.related_slide
            }
            for msg in session.chat_history
        ]
    }

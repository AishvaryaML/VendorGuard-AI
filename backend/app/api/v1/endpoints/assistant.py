from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.assistant_service import VendorAssistantService

router = APIRouter()


@router.post("/chat", response_model=AssistantChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_assistant(
    payload: AssistantChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    RAG-Grounded Vendor Assistant Chat Endpoint.
    Retrieves vendor policy evidence, constructs a grounded LLM prompt, and returns an evidence-backed answer with verified source citations.
    """
    try:
        assistant_service = VendorAssistantService()
        response = await assistant_service.chat(db=db, payload=payload)
        return response
    except ValueError as ve:
        err_str = str(ve)
        if "not found" in err_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_str
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_str
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(re)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assistant chat request failed: {str(exc)}"
        )

"""
Feedback API Routes

Handles user feedback on chat messages.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from .database import get_logs_collection, MongoDB
from .models import FeedbackRequest, FeedbackResponse
from bson import ObjectId


router = APIRouter()


@router.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback for a chat message (optionally associated with an MCP server).

    Uses atomic MongoDB updates to increment counters and append feedback entry.
    """
    try:
        logs_collection = await get_logs_collection()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {str(e)}"
        )

    # Create feedback entry
    feedback_entry = {
        "feedbackId": str(ObjectId()),
        "feedbackType": request.type,
        "feedbackText": request.comment,
        "userId": request.userId,
        "timestamp": datetime.now()
    }

    # Build atomic update operations
    update_doc = {
        "$inc": {
            "likeCount": 1 if request.type == "like" else 0,
            "dislikeCount": 1 if request.type == "dislike" else 0
        },
        "$push": {"feedbacks": feedback_entry},
        "$setOnInsert": {
            "messageId": request.messageId,
            "createdAt": datetime.now()
        }
    }

    # Include serverId if provided (for server-scoped feedback)
    if request.serverId:
        update_doc["$setOnInsert"]["serverId"] = request.serverId
        # Also store serverId in the feedback entry itself for traceability
        feedback_entry["serverId"] = request.serverId

    # Atomic update: increment counter and push feedback entry
    try:
        result = await logs_collection.update_one(
            {"messageId": request.messageId},
            update_doc,
            upsert=True
        )

        # Fetch the updated document to return current counts
        updated_doc = await logs_collection.find_one(
            {"messageId": request.messageId}
        )

        if not updated_doc:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated feedback")

        return FeedbackResponse(
            success=True,
            messageId=request.messageId,
            likeCount=updated_doc.get("likeCount", 0),
            dislikeCount=updated_doc.get("dislikeCount", 0),
            totalFeedbacks=len(updated_doc.get("feedbacks", []))
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store feedback: {str(e)}"
        )


@router.get("/api/feedback/{messageId}")
async def get_feedback(messageId: str):
    """
    Get feedback statistics for a message.
    """
    try:
        logs_collection = await get_logs_collection()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {str(e)}"
        )

    try:
        doc = await logs_collection.find_one(
            {"messageId": messageId},
            projection={"likeCount": 1, "dislikeCount": 1, "feedbacks": 1, "_id": 0}
        )

        if not doc:
            raise HTTPException(status_code=404, detail="No feedback found for this message")

        return {
            "messageId": messageId,
            "likeCount": doc.get("likeCount", 0),
            "dislikeCount": doc.get("dislikeCount", 0),
            "feedbacks": doc.get("feedbacks", [])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve feedback: {str(e)}"
        )

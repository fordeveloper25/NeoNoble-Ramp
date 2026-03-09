"""
Notification Routes - API endpoints for notifications and price alerts.

Provides:
- Notification management
- Price alerts CRUD
- WebSocket notifications
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from services.notification_service import (
    get_notification_service,
    NotificationType,
    NotificationPriority
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# Request models
class CreateAlertRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol (e.g., NENO-EUR)")
    condition: str = Field(..., regex="^(above|below|change_pct)$", description="Alert condition")
    target_value: float = Field(..., gt=0, description="Target price or percentage")


class MarkReadRequest(BaseModel):
    notification_id: str = Field(..., description="Notification ID to mark as read")


# Dependency to get user_id (simplified - in production use proper auth)
async def get_current_user_id():
    return "system_user"  # Placeholder


@router.get("/")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get user notifications.
    
    Args:
        unread_only: Return only unread notifications
        limit: Maximum number of notifications to return
    
    Returns:
        List of notifications
    """
    service = get_notification_service()
    notifications = await service.get_user_notifications(
        user_id=user_id,
        unread_only=unread_only,
        limit=limit
    )
    
    unread_count = await service.get_unread_count(user_id)
    
    return {
        "notifications": notifications,
        "count": len(notifications),
        "unread_count": unread_count
    }


@router.get("/unread-count")
async def get_unread_count(user_id: str = Depends(get_current_user_id)):
    """Get count of unread notifications."""
    service = get_notification_service()
    count = await service.get_unread_count(user_id)
    
    return {"unread_count": count}


@router.post("/mark-read")
async def mark_notification_read(
    request: MarkReadRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Mark a notification as read."""
    service = get_notification_service()
    success = await service.mark_notification_read(user_id, request.notification_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True, "notification_id": request.notification_id}


@router.post("/mark-all-read")
async def mark_all_read(user_id: str = Depends(get_current_user_id)):
    """Mark all notifications as read."""
    service = get_notification_service()
    count = await service.mark_all_read(user_id)
    
    return {"success": True, "marked_count": count}


# Price Alerts endpoints
@router.get("/alerts")
async def get_alerts(
    active_only: bool = True,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get user's price alerts.
    
    Args:
        active_only: Return only non-triggered alerts
    
    Returns:
        List of price alerts
    """
    service = get_notification_service()
    alerts = await service.get_user_alerts(user_id, active_only)
    
    return {
        "alerts": alerts,
        "count": len(alerts)
    }


@router.post("/alerts")
async def create_alert(
    request: CreateAlertRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new price alert.
    
    Args:
        request: Alert configuration
    
    Returns:
        Created alert details
    """
    service = get_notification_service()
    alert = await service.create_price_alert(
        user_id=user_id,
        symbol=request.symbol,
        condition=request.condition,
        target_value=request.target_value
    )
    
    condition_text = {
        'above': 'supera',
        'below': 'scende sotto',
        'change_pct': 'varia di'
    }.get(request.condition, '')
    
    return {
        "alert": alert.to_dict(),
        "message": f"Alert creato: riceverai una notifica quando {request.symbol} {condition_text} €{request.target_value:,.2f}"
    }


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a price alert."""
    service = get_notification_service()
    success = await service.delete_alert(user_id, alert_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"success": True, "alert_id": alert_id}


# WebSocket endpoint for real-time notifications
@router.websocket("/ws/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time notifications.
    
    Clients will receive notifications as they are created.
    """
    await websocket.accept()
    service = get_notification_service()
    service.register_websocket(user_id, websocket)
    
    try:
        # Send initial unread count
        unread_count = await service.get_unread_count(user_id)
        await websocket.send_json({
            "type": "init",
            "unread_count": unread_count
        })
        
        # Keep connection alive
        while True:
            try:
                message = await websocket.receive_text()
                # Handle ping/pong
                if message == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        pass
    finally:
        service.unregister_websocket(user_id, websocket)


# Test endpoint to send a test notification
@router.post("/test")
async def send_test_notification(user_id: str = Depends(get_current_user_id)):
    """Send a test notification (for development)."""
    service = get_notification_service()
    
    notification = await service.create_notification(
        user_id=user_id,
        type=NotificationType.INFO,
        title="Test Notification 🔔",
        message="Questa è una notifica di test. Il sistema funziona correttamente!",
        priority=NotificationPriority.MEDIUM,
        data={"test": True}
    )
    
    return {
        "success": True,
        "notification": notification.to_dict()
    }

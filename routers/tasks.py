"""
Tasks Router - Handles task creation, management, and text delivery
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional, List
from pydantic import BaseModel
import logging
import uuid
from adapters import TaskAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

class CreateTextDeliveryRequest(BaseModel):
    device_id: str
    message: str
    priority: Optional[str] = "normal"  # normal, high, urgent
    delivery_time: Optional[str] = None  # format: "2024-01-01 10:00:00", None for immediate

class UpdateTaskRequest(BaseModel):
    task_id: str
    status: Optional[str] = None  # pending, in_progress, completed, failed
    message: Optional[str] = None

class SendTextRequest(BaseModel):
    device_id: str
    text: str
    sender_name: Optional[str] = None

def verify_device_access(device_id: str, current_user: dict) -> bool:
    """Verify that the current user has access to the specified device"""
    user_devices = get_user_devices(current_user["user_id"])
    user_device_ids = [device.device_id for device in user_devices]
    return device_id in user_device_ids

@router.post("/create")
def create_text_delivery_task(
    request: CreateTextDeliveryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a text delivery task for a device.
    Only devices assigned to the current user are accessible.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Convert delivery_time to Unix timestamp if provided
    send_time = None
    if request.delivery_time:
        from datetime import datetime
        try:
            dt = datetime.strptime(request.delivery_time, "%Y-%m-%d %H:%M:%S")
            send_time = int(dt.timestamp())
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid delivery_time format. Use: YYYY-MM-DD HH:MM:SS")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Creating task for device {request.device_id}")
    
    # Build request using adapter
    task_data = TaskAdapter.build_create_task_request(
        device_ids=[request.device_id],
        content=request.message,
        send_time=send_time
    )
    
    # Call manufacturer API
    result = manufacturer_api.create_text_delivery_task(task_data)
    
    # Parse response using adapter with correlation ID
    task_dto = TaskAdapter.parse_task_response(result, correlation_id=correlation_id)
    
    if task_dto:
        return {
            "success": True,
            "task_id": task_dto.task_id,
            "device_id": request.device_id,
            "message": request.message,
            "status": task_dto.status or "pending",
            "created_at": task_dto.created_at,
            "delivery_time": request.delivery_time or "immediate"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to create task: {result.get('message', 'Unknown error')}"
        )

@router.get("/")
def get_task_list(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    page: Optional[int] = Query(1, description="Page number"),
    page_size: Optional[int] = Query(20, description="Items per page")
):
    """
    Get list of tasks for the current user.
    Only shows tasks for devices assigned to the user.
    """
    # Get user's devices for filtering
    user_devices = get_user_devices(current_user["user_id"])
    user_device_ids = [device.device_id for device in user_devices]
    
    if device_id and device_id not in user_device_ids:
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Getting task list (page={page})")
    
    # Build request using adapter
    query_data = TaskAdapter.build_task_list_request(
        page=page,
        page_size=page_size,
        device_id=device_id,
        status=status
    )
    
    # Call manufacturer API
    result = manufacturer_api.get_task_list(query_data)
    
    # Parse response using adapter with correlation ID
    tasks = TaskAdapter.parse_task_list_response(result, correlation_id)
    
    # Filter tasks to only include user's devices
    filtered_tasks = [
        task.model_dump(by_alias=False)
        for task in tasks
        if task.device_id in user_device_ids
    ]
    
    return {
        "success": True,
        "tasks": filtered_tasks,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": len(filtered_tasks),
            "total_pages": (len(filtered_tasks) + page_size - 1) // page_size
        },
        "filters": {
            "status": status,
            "device_id": device_id
        }
    }

@router.get("/{task_id}")
def get_task_details(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific task.
    """
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Getting task details for {task_id}")
    
    task_data = {"taskId": task_id}
    result = manufacturer_api.get_task_details(task_data)
    
    # Parse response using adapter with correlation ID
    task_dto = TaskAdapter.parse_task_response(result, task_id, correlation_id)
    
    if task_dto:
        # Verify user has access to the device this task belongs to
        if not verify_device_access(task_dto.device_id, current_user):
            raise HTTPException(status_code=403, detail="Task not accessible")
        
        return {
            "success": True,
            "task": task_dto.model_dump(by_alias=False)
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get task details: {result.get('message', 'Unknown error')}"
        )

@router.put("/{task_id}/status")
def update_task_status(
    task_id: str,
    request: UpdateTaskRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update task status or information.
    Only the task creator can update tasks.
    """
    # First get task details to verify ownership
    task_data = {"taskId": task_id}
    result = manufacturer_api.get_task_details(task_data)
    
    if result.get("code") != 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = result.get("data", {})
    
    # Verify user has access to the device this task belongs to
    device_id = task_info.get("deviceId")
    if device_id and not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Task not accessible")
    
    # Update task
    update_data = {
        "taskId": task_id,
        "status": request.status,
        "message": request.message,
        "updatedBy": current_user["invoice_no"]
    }
    result = manufacturer_api.update_task_status(update_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "task_id": task_id,
            "updated_status": request.status,
            "message": "Task updated successfully"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to update task: {result.get('message', 'Unknown error')}"
        )

@router.get("/{task_id}/result")
def get_task_execution_result(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get task execution results and delivery status.
    """
    # Generate correlation ID for this request
    correlation_id = str(uuid.uuid4())[:8]
    logger.info(f"[{correlation_id}] Getting task results for {task_id}")
    
    task_data = {"taskId": task_id}
    result = manufacturer_api.get_task_results(task_data)
    
    # Parse response using adapter with correlation ID
    result_dto = TaskAdapter.parse_task_result_response(result, task_id, correlation_id)
    
    if result_dto:
        # Verify user has access to this task (check device ownership)
        if not verify_device_access(result_dto.device_id, current_user):
            raise HTTPException(status_code=403, detail="Task not accessible")
        
        return {
            "success": True,
            "task_id": task_id,
            "execution_result": result_dto.model_dump(by_alias=False, exclude={"task_id", "device_id"})
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get task result: {result.get('message', 'Unknown error')}"
        )

@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a task.
    Only the task creator can delete tasks.
    """
    # First verify ownership by getting task details
    task_data = {"taskId": task_id}
    details_result = manufacturer_api.get_task_details(task_data)
    
    if details_result.get("code") != 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = details_result.get("data", {})
    device_id = task_info.get("deviceId")
    
    if device_id and not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Task not accessible")
    
    # Delete task
    result = manufacturer_api.delete_task(task_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "task_id": task_id,
            "message": "Task deleted successfully"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to delete task: {result.get('message', 'Unknown error')}"
        )

@router.post("/send-text")
def send_text_message(
    request: SendTextRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a text message directly to a device (immediate delivery).
    This is a simpler interface compared to creating a delivery task.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Build request using adapter
    text_data = TaskAdapter.build_text_delivery_request(
        device_ids=[request.device_id],
        content=request.text
    )
    
    # Call manufacturer API
    result = manufacturer_api.send_text(text_data)
    
    if result.get("code") in (200, 0):
        data = result.get("data", {})
        return {
            "success": True,
            "device_id": request.device_id,
            "text": request.text,
            "sent_at": TaskAdapter.convert_timestamp_to_ms(data.get("sentAt")) if data.get("sentAt") else None,
            "message": "Text sent successfully"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to send text: {result.get('message', 'Unknown error')}"
        )



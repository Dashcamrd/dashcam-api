"""
Tasks Router - Handles task creation, management, and text delivery
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional, List
from pydantic import BaseModel

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
    
    # Call manufacturer API
    task_data = {
        "deviceId": request.device_id,
        "message": request.message,
        "priority": request.priority,
        "deliveryTime": request.delivery_time,
        "createdBy": current_user["invoice_no"]
    }
    result = manufacturer_api.create_text_delivery_task(task_data)
    
    if result.get("code") == 0:
        task_info = result.get("data", {})
        return {
            "success": True,
            "task_id": task_info.get("taskId"),
            "device_id": request.device_id,
            "message": request.message,
            "status": "pending",
            "created_at": task_info.get("createdAt"),
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
    
    # Call manufacturer API
    query_data = {
        "createdBy": current_user["invoice_no"],
        "status": status,
        "deviceId": device_id,
        "page": page,
        "pageSize": page_size
    }
    result = manufacturer_api.get_task_list(query_data)
    
    if result.get("code") == 0:
        tasks_data = result.get("data", {})
        tasks = tasks_data.get("tasks", [])
        
        # Filter tasks to only include user's devices
        filtered_tasks = []
        for task in tasks:
            if task.get("deviceId") in user_device_ids:
                filtered_tasks.append({
                    "task_id": task.get("id"),
                    "device_id": task.get("deviceId"),
                    "message": task.get("message"),
                    "status": task.get("status"),
                    "priority": task.get("priority"),
                    "created_at": task.get("createdAt"),
                    "delivery_time": task.get("deliveryTime"),
                    "completed_at": task.get("completedAt"),
                    "result": task.get("result")
                })
        
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
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get tasks: {result.get('message', 'Unknown error')}"
        )

@router.get("/{task_id}")
def get_task_details(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information about a specific task.
    """
    task_data = {"taskId": task_id}
    result = manufacturer_api.get_task_details(task_data)
    
    if result.get("code") == 0:
        task_info = result.get("data", {})
        
        # Verify user has access to the device this task belongs to
        device_id = task_info.get("deviceId")
        if device_id and not verify_device_access(device_id, current_user):
            raise HTTPException(status_code=403, detail="Task not accessible")
        
        return {
            "success": True,
            "task": {
                "task_id": task_info.get("id"),
                "device_id": task_info.get("deviceId"),
                "message": task_info.get("message"),
                "status": task_info.get("status"),
                "priority": task_info.get("priority"),
                "created_at": task_info.get("createdAt"),
                "delivery_time": task_info.get("deliveryTime"),
                "completed_at": task_info.get("completedAt"),
                "result": task_info.get("result"),
                "error_message": task_info.get("errorMessage"),
                "retry_count": task_info.get("retryCount"),
                "created_by": task_info.get("createdBy")
            }
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
    task_data = {"taskId": task_id}
    result = manufacturer_api.get_task_results(task_data)
    
    if result.get("code") == 0:
        result_data = result.get("data", {})
        
        # Verify user has access to this task (check device ownership)
        device_id = result_data.get("deviceId")
        if device_id and not verify_device_access(device_id, current_user):
            raise HTTPException(status_code=403, detail="Task not accessible")
        
        return {
            "success": True,
            "task_id": task_id,
            "execution_result": {
                "status": result_data.get("status"),
                "delivered_at": result_data.get("deliveredAt"),
                "acknowledged_at": result_data.get("acknowledgedAt"),
                "delivery_attempts": result_data.get("deliveryAttempts"),
                "error_details": result_data.get("errorDetails"),
                "device_response": result_data.get("deviceResponse")
            }
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
    
    # Call manufacturer API
    text_data = {
        "deviceId": request.device_id,
        "text": request.text,
        "senderName": request.sender_name or current_user["name"],
        "sentBy": current_user["invoice_no"]
    }
    result = manufacturer_api.send_text(text_data)
    
    if result.get("code") == 0:
        return {
            "success": True,
            "device_id": request.device_id,
            "text": request.text,
            "sent_at": result.get("data", {}).get("sentAt"),
            "message": "Text sent successfully"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to send text: {result.get('message', 'Unknown error')}"
        )

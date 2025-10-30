"""
Task Adapter - Maps vendor Task API responses to stable DTOs.
"""
import logging
from typing import Optional, Dict, Any, List
from models.dto import TaskDto, TaskResultDto
from .base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class TaskAdapter(BaseAdapter):
    """Adapter for task-related endpoints (text delivery, task management)"""
    
    @staticmethod
    def parse_task_response(
        vendor_response: Dict[str, Any],
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Optional[TaskDto]:
        """
        Parse vendor task response into TaskDto.
        
        Args:
            vendor_response: Raw vendor API response
            task_id: Optional task ID (if known)
        
        Returns:
            TaskDto or None if not found
        """
        try:
            # Validate response code using config
            success_codes = TaskAdapter.get_response_success_codes("task_get_details", [200, 0])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"Task response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return None
            
            data = vendor_response.get("data", {})
            
            # Task data might be at root of data or nested
            task_data = data.get("task") or data
            
            task_id = task_id or task_data.get("id") or task_data.get("taskId")
            if not task_id:
                return None
            
            return TaskDto(
                taskId=task_id,
                deviceId=task_data.get("deviceId") or task_data.get("device_id", ""),
                content=task_data.get("content") or task_data.get("message"),
                status=task_data.get("status"),
                priority=task_data.get("priority"),
                createdAt=TaskAdapter.convert_timestamp_to_ms(task_data.get("createdAt")) if task_data.get("createdAt") else None,
                sendTime=TaskAdapter.convert_timestamp_to_ms(task_data.get("sendTime")) if task_data.get("sendTime") else None,
                completedAt=TaskAdapter.convert_timestamp_to_ms(task_data.get("completedAt")) if task_data.get("completedAt") else None,
                result=task_data.get("result")
            )
            
        except Exception as e:
            error_msg = f"Error parsing task response: {e}"
            if correlation_id:
                logger.error(f"[{correlation_id}] {error_msg}", exc_info=True)
            else:
                logger.error(error_msg, exc_info=True)
            return None
    
    @staticmethod
    def parse_task_list_response(
        vendor_response: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> List[TaskDto]:
        """
        Parse vendor task list response into list of TaskDto.
        
        Args:
            vendor_response: Raw vendor API response
        
        Returns:
            List of TaskDto objects
        """
        tasks: List[TaskDto] = []
        
        try:
            # Validate response code using config
            success_codes = TaskAdapter.get_response_success_codes("task_get_list", [200, 0])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"Task list response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return tasks
            
            data = vendor_response.get("data", {})
            tasks_raw = data.get("tasks", []) or data.get("list", [])
            
            for t in tasks_raw:
                try:
                    task_id = t.get("id") or t.get("taskId")
                    if not task_id:
                        continue
                    
                    tasks.append(TaskDto(
                        taskId=task_id,
                        deviceId=t.get("deviceId") or t.get("device_id", ""),
                        content=t.get("content") or t.get("message"),
                        status=t.get("status"),
                        priority=t.get("priority"),
                        createdAt=TaskAdapter.convert_timestamp_to_ms(t.get("createdAt")) if t.get("createdAt") else None,
                        sendTime=TaskAdapter.convert_timestamp_to_ms(t.get("sendTime")) if t.get("sendTime") else None,
                        completedAt=TaskAdapter.convert_timestamp_to_ms(t.get("completedAt")) if t.get("completedAt") else None,
                        result=t.get("result")
                    ))
                except Exception as e:
                    logger.debug(f"Error parsing task entry: {e}, skipping")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing task list response: {e}", exc_info=True)
        
        return tasks
    
    @staticmethod
    def parse_task_result_response(
        vendor_response: Dict[str, Any],
        task_id: str,
        correlation_id: Optional[str] = None
    ) -> Optional[TaskResultDto]:
        """
        Parse vendor task result response into TaskResultDto.
        
        Args:
            vendor_response: Raw vendor API response
            task_id: Task ID
        
        Returns:
            TaskResultDto or None if not found
        """
        try:
            # Validate response code using config
            success_codes = TaskAdapter.get_response_success_codes("task_get_results", [200, 0])
            code = vendor_response.get("code")
            
            if code not in success_codes:
                error_msg = f"Task result response has non-success code: {code}"
                if correlation_id:
                    logger.warning(f"[{correlation_id}] {error_msg}")
                else:
                    logger.warning(error_msg)
                return None
            
            data = vendor_response.get("data", {})
            
            return TaskResultDto(
                taskId=task_id,
                deviceId=data.get("deviceId") or data.get("device_id", ""),
                status=data.get("status"),
                deliveredAt=TaskAdapter.convert_timestamp_to_ms(data.get("deliveredAt")) if data.get("deliveredAt") else None,
                acknowledgedAt=TaskAdapter.convert_timestamp_to_ms(data.get("acknowledgedAt")) if data.get("acknowledgedAt") else None,
                deliveryAttempts=data.get("deliveryAttempts") or data.get("delivery_attempts"),
                errorDetails=data.get("errorDetails") or data.get("error_details"),
                deviceResponse=data.get("deviceResponse") or data.get("device_response")
            )
            
        except Exception as e:
            logger.error(f"Error parsing task result response: {e}", exc_info=True)
            return None
    
    @staticmethod
    def build_create_task_request(
        device_ids: List[str],
        content: str,
        send_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build request for create task endpoint.
        
        Args:
            device_ids: List of device IDs
            content: Message content
            send_time: Optional Unix timestamp in seconds for scheduled delivery
        
        Returns:
            Request dictionary
        """
        request: Dict[str, Any] = {
            "deviceIds": device_ids,
            "content": content
        }
        
        if send_time:
            request["sendTime"] = send_time
        
        return request
    
    @staticmethod
    def build_task_list_request(
        page: int = 1,
        page_size: int = 10,
        device_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Build request for task list endpoint.
        
        Args:
            page: Page number (starts at 1)
            page_size: Items per page
            device_id: Optional device ID filter
            status: Optional status filter
            start_time: Optional start time (Unix seconds)
            end_time: Optional end time (Unix seconds)
        
        Returns:
            Request dictionary
        """
        request: Dict[str, Any] = {
            "page": page,
            "pageSize": page_size
        }
        
        if device_id:
            request["deviceId"] = device_id
        if status:
            request["status"] = status
        if start_time:
            request["startTime"] = start_time
        if end_time:
            request["endTime"] = end_time
        
        return request
    
    @staticmethod
    def build_text_delivery_request(
        device_ids: List[str],
        content: str
    ) -> Dict[str, Any]:
        """
        Build request for text delivery endpoint.
        
        Args:
            device_ids: List of device IDs
            content: Text message content
        
        Returns:
            Request dictionary
        """
        return {
            "deviceIds": device_ids,
            "content": content
        }


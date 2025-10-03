"""
Reports Router - Handles statistics and reporting
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from services.auth_service import get_current_user, get_user_devices
from services.manufacturer_api_service import manufacturer_api
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/reports", tags=["Reports"])

class StatisticsRequest(BaseModel):
    device_id: str
    start_date: str  # format: "2024-01-01"
    end_date: str    # format: "2024-01-01"
    stat_type: Optional[str] = "general"  # general, driving, alarms, etc.

class VehicleDetailRequest(BaseModel):
    device_id: str
    date: str        # format: "2024-01-01"
    detail_type: Optional[str] = "all"  # all, driving, stops, alarms

def verify_device_access(device_id: str, current_user: dict) -> bool:
    """Verify that the current user has access to the specified device"""
    user_devices = get_user_devices(current_user["user_id"])
    user_device_ids = [device.device_id for device in user_devices]
    return device_id in user_device_ids

@router.get("/statistics/{device_id}")
def get_vehicle_statistics(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    stat_type: str = Query("general", description="Statistics type")
):
    """
    Get vehicle/fleet statistics for a device within a date range.
    Only devices assigned to the current user are accessible.
    """
    # Verify user has access to this device
    if not verify_device_access(device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    query_data = {
        "deviceId": device_id,
        "startDate": start_date,
        "endDate": end_date,
        "statType": stat_type
    }
    result = manufacturer_api.get_vehicle_statistics(query_data)
    
    if result.get("code") == 0:
        stats_data = result.get("data", {})
        
        # Process and enhance statistics data
        processed_stats = {
            "device_id": device_id,
            "date_range": f"{start_date} to {end_date}",
            "stat_type": stat_type,
            "summary": {
                "total_distance": stats_data.get("totalDistance", 0),
                "total_duration": stats_data.get("totalDuration", 0),
                "average_speed": stats_data.get("averageSpeed", 0),
                "max_speed": stats_data.get("maxSpeed", 0),
                "total_stops": stats_data.get("totalStops", 0),
                "fuel_consumption": stats_data.get("fuelConsumption", 0),
                "idle_time": stats_data.get("idleTime", 0)
            },
            "daily_breakdown": stats_data.get("dailyBreakdown", []),
            "route_analysis": stats_data.get("routeAnalysis", {}),
            "efficiency_metrics": {
                "fuel_efficiency": stats_data.get("fuelEfficiency", 0),
                "driving_score": stats_data.get("drivingScore", 0),
                "utilization_rate": stats_data.get("utilizationRate", 0)
            },
            "alarms_summary": {
                "total_alarms": stats_data.get("totalAlarms", 0),
                "critical_alarms": stats_data.get("criticalAlarms", 0),
                "alarm_types": stats_data.get("alarmTypes", {})
            }
        }
        
        return {
            "success": True,
            "statistics": processed_stats
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get statistics: {result.get('message', 'Unknown error')}"
        )

@router.post("/vehicle-details")
def get_vehicle_details(
    request: VehicleDetailRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Query detailed vehicle information for a specific date.
    """
    # Verify user has access to this device
    if not verify_device_access(request.device_id, current_user):
        raise HTTPException(status_code=403, detail="Device not accessible")
    
    # Call manufacturer API
    query_data = {
        "deviceId": request.device_id,
        "date": request.date,
        "detailType": request.detail_type
    }
    result = manufacturer_api.get_vehicle_details(query_data)
    
    if result.get("code") == 0:
        details_data = result.get("data", {})
        
        return {
            "success": True,
            "device_id": request.device_id,
            "date": request.date,
            "detail_type": request.detail_type,
            "vehicle_details": {
                "trips": details_data.get("trips", []),
                "stops": details_data.get("stops", []),
                "alarms": details_data.get("alarms", []),
                "maintenance_alerts": details_data.get("maintenanceAlerts", []),
                "driver_behavior": details_data.get("driverBehavior", {}),
                "route_details": details_data.get("routeDetails", {})
            },
            "summary": {
                "total_trips": len(details_data.get("trips", [])),
                "total_stops": len(details_data.get("stops", [])),
                "total_distance": details_data.get("totalDistance", 0),
                "total_duration": details_data.get("totalDuration", 0)
            }
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to get vehicle details: {result.get('message', 'Unknown error')}"
        )

@router.get("/fleet-summary")
def get_fleet_summary(
    current_user: dict = Depends(get_current_user),
    date: str = Query(..., description="Date for summary (YYYY-MM-DD)")
):
    """
    Get fleet summary for all user devices on a specific date.
    Provides a dashboard overview of all vehicles.
    """
    user_devices = get_user_devices(current_user["user_id"])
    
    if not user_devices:
        return {
            "success": True,
            "fleet_summary": {
                "total_vehicles": 0,
                "active_vehicles": 0,
                "total_distance": 0,
                "total_duration": 0,
                "avg_utilization": 0,
                "total_alarms": 0,
                "vehicle_summaries": []
            },
            "message": "No devices assigned to this user"
        }
    
    fleet_summary = {
        "total_vehicles": len(user_devices),
        "active_vehicles": 0,
        "total_distance": 0,
        "total_duration": 0,
        "total_alarms": 0,
        "vehicle_summaries": []
    }
    
    for device in user_devices:
        try:
            # Get statistics for this device
            query_data = {
                "deviceId": device.device_id,
                "startDate": date,
                "endDate": date,
                "statType": "general"
            }
            result = manufacturer_api.get_vehicle_statistics(query_data)
            
            if result.get("code") == 0:
                stats_data = result.get("data", {})
                
                device_distance = stats_data.get("totalDistance", 0)
                device_duration = stats_data.get("totalDuration", 0)
                device_alarms = stats_data.get("totalAlarms", 0)
                
                # Update fleet totals
                fleet_summary["total_distance"] += device_distance
                fleet_summary["total_duration"] += device_duration
                fleet_summary["total_alarms"] += device_alarms
                
                if device_distance > 0:  # Vehicle was active
                    fleet_summary["active_vehicles"] += 1
                
                fleet_summary["vehicle_summaries"].append({
                    "device_id": device.device_id,
                    "device_name": device.name,
                    "distance": device_distance,
                    "duration": device_duration,
                    "max_speed": stats_data.get("maxSpeed", 0),
                    "alarms": device_alarms,
                    "status": "active" if device_distance > 0 else "inactive"
                })
            else:
                # Include device even if stats fail
                fleet_summary["vehicle_summaries"].append({
                    "device_id": device.device_id,
                    "device_name": device.name,
                    "distance": 0,
                    "duration": 0,
                    "max_speed": 0,
                    "alarms": 0,
                    "status": "no_data",
                    "error": result.get("message", "Unknown error")
                })
                
        except Exception as e:
            fleet_summary["vehicle_summaries"].append({
                "device_id": device.device_id,
                "device_name": device.name,
                "distance": 0,
                "duration": 0,
                "max_speed": 0,
                "alarms": 0,
                "status": "error",
                "error": str(e)
            })
    
    # Calculate utilization rate
    fleet_summary["avg_utilization"] = (
        fleet_summary["active_vehicles"] / fleet_summary["total_vehicles"] * 100
        if fleet_summary["total_vehicles"] > 0 else 0
    )
    
    return {
        "success": True,
        "date": date,
        "fleet_summary": fleet_summary
    }

@router.get("/comparison")
def get_comparative_report(
    current_user: dict = Depends(get_current_user),
    device_ids: str = Query(..., description="Comma-separated device IDs"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
):
    """
    Compare statistics across multiple devices.
    Useful for fleet managers to compare vehicle performance.
    """
    device_id_list = [d.strip() for d in device_ids.split(",") if d.strip()]
    
    # Verify user has access to all requested devices
    user_devices = get_user_devices(current_user["user_id"])
    user_device_ids = [device.device_id for device in user_devices]
    
    for device_id in device_id_list:
        if device_id not in user_device_ids:
            raise HTTPException(status_code=403, detail=f"Device {device_id} not accessible")
    
    comparison_data = {
        "date_range": f"{start_date} to {end_date}",
        "devices": [],
        "comparison_metrics": {
            "best_fuel_efficiency": {"device_id": None, "value": 0},
            "highest_utilization": {"device_id": None, "value": 0},
            "most_distance": {"device_id": None, "value": 0},
            "safest_driver": {"device_id": None, "value": 0}
        }
    }
    
    for device_id in device_id_list:
        try:
            query_data = {
                "deviceId": device_id,
                "startDate": start_date,
                "endDate": end_date,
                "statType": "general"
            }
            result = manufacturer_api.get_vehicle_statistics(query_data)
            
            if result.get("code") == 0:
                stats_data = result.get("data", {})
                
                # Find device name
                device = next((d for d in user_devices if d.device_id == device_id), None)
                device_name = device.name if device else device_id
                
                device_stats = {
                    "device_id": device_id,
                    "device_name": device_name,
                    "total_distance": stats_data.get("totalDistance", 0),
                    "total_duration": stats_data.get("totalDuration", 0),
                    "fuel_efficiency": stats_data.get("fuelEfficiency", 0),
                    "utilization_rate": stats_data.get("utilizationRate", 0),
                    "driving_score": stats_data.get("drivingScore", 0),
                    "total_alarms": stats_data.get("totalAlarms", 0),
                    "average_speed": stats_data.get("averageSpeed", 0)
                }
                
                comparison_data["devices"].append(device_stats)
                
                # Update comparison metrics
                if device_stats["fuel_efficiency"] > comparison_data["comparison_metrics"]["best_fuel_efficiency"]["value"]:
                    comparison_data["comparison_metrics"]["best_fuel_efficiency"] = {
                        "device_id": device_id, "device_name": device_name, "value": device_stats["fuel_efficiency"]
                    }
                
                if device_stats["utilization_rate"] > comparison_data["comparison_metrics"]["highest_utilization"]["value"]:
                    comparison_data["comparison_metrics"]["highest_utilization"] = {
                        "device_id": device_id, "device_name": device_name, "value": device_stats["utilization_rate"]
                    }
                
                if device_stats["total_distance"] > comparison_data["comparison_metrics"]["most_distance"]["value"]:
                    comparison_data["comparison_metrics"]["most_distance"] = {
                        "device_id": device_id, "device_name": device_name, "value": device_stats["total_distance"]
                    }
                
                if device_stats["driving_score"] > comparison_data["comparison_metrics"]["safest_driver"]["value"]:
                    comparison_data["comparison_metrics"]["safest_driver"] = {
                        "device_id": device_id, "device_name": device_name, "value": device_stats["driving_score"]
                    }
                    
        except Exception as e:
            # Include device with error status
            device = next((d for d in user_devices if d.device_id == device_id), None)
            comparison_data["devices"].append({
                "device_id": device_id,
                "device_name": device.name if device else device_id,
                "error": str(e),
                "status": "error"
            })
    
    return {
        "success": True,
        "comparison": comparison_data,
        "total_devices_compared": len(device_id_list)
    }

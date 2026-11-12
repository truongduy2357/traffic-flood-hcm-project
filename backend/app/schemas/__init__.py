"""
Package chứa các Pydantic Schemas phục vụ Request & Response Validation cho FastAPI.
"""

from app.schemas.flood_report import (
    FloodReportBase,
    FloodReportCreate,
    FloodReportUpdate,
    FloodReportResponse,
)
from app.schemas.user import (
    UserRole,
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    Token,
    TokenData,
)
from app.schemas.spatial import (
    PointCoordinate,
    NearbyQuery,
    BoundingBoxQuery,
    RouteCheckRequest,
    InterceptedFloodItem,
    RouteCheckResponse,
    GeoJSONGeometry,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
)

__all__ = [
    # Flood Report
    "FloodReportBase",
    "FloodReportCreate",
    "FloodReportUpdate",
    "FloodReportResponse",
    # User & Auth
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenData",
    # Spatial & Routing
    "PointCoordinate",
    "NearbyQuery",
    "BoundingBoxQuery",
    "RouteCheckRequest",
    "InterceptedFloodItem",
    "RouteCheckResponse",
    "GeoJSONGeometry",
    "GeoJSONFeature",
    "GeoJSONFeatureCollection",
]

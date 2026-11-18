
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
    "FloodReportBase",
    "FloodReportCreate",
    "FloodReportUpdate",
    "FloodReportResponse",
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
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

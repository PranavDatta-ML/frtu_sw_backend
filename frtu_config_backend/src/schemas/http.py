from pydantic import Field, HttpUrl
from typing import Dict, Any, Optional

from src.schemas.base import BaseSchema
from src.enums.http import HTTPMethods


class HTTPSchema(BaseSchema):
    """
    Schema for the request configuration.
    """
    endpoint: HttpUrl = Field(..., description="The endpoint URL for the API call.")
    method: HTTPMethods = Field(..., description="HTTP method to use for the request, such as GET, POST, etc.")
    body: Optional[Dict[str, Any]] = Field(None, description="The body of the request containing additional JSON data.")
    header: Optional[Dict[str, Any]] = Field(None, description="The headers for the request, including authorization and content type.")
import traceback
from typing import Any

from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class UnifiedJSONResponse(JSONResponse):
    """Custom JSONResponse class that wraps standard JSON output in a unified envelope using snake_case and booleans."""

    def render(self, content: Any) -> bytes:
        # If content is already wrapped in the unified error/success envelope, skip wrapping
        if isinstance(content, dict) and "status" in content and ("data" in content or "message" in content):
            return super().render(content)

        # If content is a pagination envelope returned by services, skip wrapping
        if isinstance(content, dict) and "data" in content and "page" in content and "total" in content:
            return super().render(content)

        # Handle pagination metadata if it matches PaginatedResponse schema structure
        meta = None
        data_content = content
        if isinstance(content, dict) and "items" in content and "total" in content:
            meta = {
                "total": content.get("total"),
                "page": content.get("page"),
                "page_size": content.get("page_size"),
                "pages": content.get("pages")
            }
            data_content = content.get("items", [])

        # Wrap in success envelope
        envelope = {
            "status": True,
            "data": data_content,
            "message": None
        }
        if meta is not None:
            envelope["meta"] = meta

        return super().render(envelope)


async def validation_exception_handler(request, exc: RequestValidationError):
    """Handle request validation errors and return standard error envelope with field details in `snake_case."""
    errors_list = []
    for error in exc.errors():
        loc = error["loc"]
        # Skip top level location identifiers like 'body', 'query' for user-friendly paths
        if len(loc) > 1:
            field_path = ".".join(str(x) for x in loc[1:])
        else:
            field_path = ".".join(str(x) for x in loc)
            
        errors_list.append({
            "field": field_path,
            "message": error["msg"]
        })
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "status": False,
            "data": {
                "errors": errors_list
            },
            "message": "Validation failed"
        }
    )


async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions and return standard error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": False,
            "data": None,
            "message": exc.detail
        }
    )


async def general_exception_handler(request, exc: Exception):
    """Handle generic unhandled exceptions to avoid leaking internal tracebacks."""
    # For development, we print the traceback to stdout/stderr
    print("Unhandled Server Exception:")
    traceback.print_exc()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": False,
            "data": None,
            "message": "Internal Server Error"
        }
    )

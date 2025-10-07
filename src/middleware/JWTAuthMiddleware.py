from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import status
import jwt
from typing import Callable, Set


class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app,
            secret_key: str,
            algorithm: str = "HS256",
            exclude_paths: Set[str] = None,
            audience: str = None,
            issuer: str = None,
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.exclude_paths = exclude_paths or set()
        self.audience = audience
        self.issuer = issuer

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                content="Missing or invalid authorization header",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        token = auth_header.split(" ")[1]

        try:
            # Verify and decode the JWT token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
            )

            # Add user info to request state for use in endpoints
            request.state.user = payload

        except jwt.ExpiredSignatureError:
            return Response(
                content="Token has expired",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        except jwt.InvalidTokenError:
            return Response(
                content="Invalid token",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # Continue to the next middleware/endpoint
        response = await call_next(request)
<<<<<<< HEAD
        return response
=======
        return response
>>>>>>> 7ae3bb74c3c3357b879e38d68f3cb3324b62eb07

from enum import Enum
from fastapi.responses import JSONResponse


class HttpStatusCode(Enum):
    """
    Enum for HTTP status codes.
    """
    OK = (200, 'OK', 'Success')
    CREATED = (201, 'CREATED', 'Success')
    BAD_REQUEST = (400, 'BAD_REQUEST', 'Malformed request syntax')
    NOT_AUTHENTICATED = (401, 'NOT_AUTHENTICATED', 'Please authenticate first')
    ACCESS_DENIED = (403, 'ACCESS_DENIED', "You don't have access to this entity")
    NOT_FOUND = (404, 'NOT_FOUND', "Entity doesn't exist")
    METHOD_NOT_SUPPORTED = (405, 'METHOD_NOT_SUPPORTED', 'HTTP method used is not supported for this entity')
    ALREADY_EXISTS = (409, 'ALREADY_EXISTS', 'This entity already exists')
    GONE = (410, 'GONE', 'This entity is no longer available')
    SERVER_ERROR = (500, 'SERVER_ERROR', 'Internal server error, while processing your request')

    def __init__(self, http_code: int, code: str, message: str):
        """
        Initializes an instance of the HttpStatusCode class.
        """
        self.http_code: int = http_code
        self.code: str = code
        self.message: str = message

    def __str__(self) -> str:
        """
        Returns a string representation of the HttpStatusCode object.
        """
        return f"<HTTP_CODE={self.http_code} CODE={self.code} MESSAGE={self.message}>"

    def response(self, message: str = None, data: dict = None) -> JSONResponse:
        """
        Returns a JSONResponse object with the provided HTTP status code, code, and message.
        
        :param message: Optional custom message to override the default message.
        :param data: Optional data to include in the response.
        :return: JSONResponse
        """
        if message:
            self.message = message

        response_content = {
            'http_code': self.http_code,
            'code': self.code,
            'message': self.message,
        }

        if data is not None:
            response_content['data'] = data
        return JSONResponse(response_content, status_code=self.http_code)


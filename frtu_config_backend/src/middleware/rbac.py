from fastapi import HTTPException

class RBACError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=403, detail=message)

class SelfEditError(RBACError):
    def __init__(self):
        super().__init__("You cannot modify your own roles or permissions")

class ChildScopeError(RBACError):
    def __init__(self):
        super().__init__("You can modify only child-created resources")

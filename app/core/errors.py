from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(self, code: str, status_code: int, detail: str | None = None):
        super().__init__(status_code=status_code, detail=detail or code)
        self.code = code


def NotFound(code: str = "not_found"):
    return AppError(code, status.HTTP_404_NOT_FOUND)


def Conflict(code: str):
    return AppError(code, status.HTTP_409_CONFLICT)


def Forbidden(code: str = "forbidden"):
    return AppError(code, status.HTTP_403_FORBIDDEN)


def Unauthorized(code: str = "unauthorized"):
    return AppError(code, status.HTTP_401_UNAUTHORIZED)


def BadRequest(code: str):
    return AppError(code, status.HTTP_422_UNPROCESSABLE_ENTITY)

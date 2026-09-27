from pydantic import BaseModel


class AssignmentRequest(BaseModel):
    assignment_id: str
    order_id: str
    executor_id: str
    decided_at: str


class AssignmentResponse(BaseModel):
    assignment_id: str
    order_id: str
    executor_id: str
    status: str = "confirmed"
    confirmed_at: str


class AssignmentError(BaseModel):
    code: str
    message: str
    retryable: bool = False

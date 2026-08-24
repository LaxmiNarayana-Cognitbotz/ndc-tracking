from pydantic import BaseModel


class EmployeeEmailCreate(BaseModel):
    person_number: int
    employee_name: str
    email: str


class EmployeeEmailUpdate(BaseModel):
    person_number: int
    employee_name: str
    email: str

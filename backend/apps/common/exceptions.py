from rest_framework.exceptions import APIException
from rest_framework import status


class DomainError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Operation not allowed."
    default_code = "domain_error"


class FinancialYearLocked(DomainError):
    default_detail = "Financial year is closed and read-only."
    default_code = "fy_locked"


class LicenseError(DomainError):
    default_detail = "License does not permit this operation."
    default_code = "license_error"

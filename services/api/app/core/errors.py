from dataclasses import dataclass


@dataclass
class Problem(Exception):
    status: int
    code: str
    message: str


def not_found() -> Problem:
    return Problem(404, "JOB_NOT_FOUND", "Job not found")

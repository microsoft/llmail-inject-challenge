# Classes that represent information and don't do any work
from .job import JobMessage, JobRecord, JobResult
from .leaderboard import Leaderboard
from .scenario import Scenario
from .team import Team
from .user import User

from dataclasses import asdict
from typing import T


def to_api(entity: T, fields: list[str] | None = None) -> dict:
    """
    Converts a dataclass entity to a dictionary with only the API fields
    which are non-null.

    The entity itself is expected to be a dataclass and may also have a `__api_fields__`
    attribute that specifies which fields should be included in the API response.

    :param entity:
        The entity to convert to a dictionary for returning in an API response.

    :param fields:
        The list of fields to include in the API response. If not provided, all fields
        are included. If provided, only the fields in this list are included.

    :return:
        A dictionary with only the API fields of the entity that are non-null.
    """

    api_fields = getattr(entity.__class__, "__api_fields__", None)
    if fields is not None:
        api_fields = [f for f in fields if f in api_fields] if api_fields is not None else fields

    return {
        k: v for k, v in asdict(entity).items() if v is not None and (api_fields is None or k in api_fields)
    }


def to_telemetry_attributes(entity: T) -> dict:
    """
    Converts a dataclass entity to a dictionary with only the telemetry fields
    which are non-null.

    The entity itself is expected to be a dataclass and may also have a `__api_fields__`
    attribute that specifies which fields should be included in the telemetry attributes.
    """

    return {
        k: v if isinstance(v, (str, bool, int, float, bytes)) else repr(v) for k, v in to_api(entity).items()
    }

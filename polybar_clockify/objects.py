from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import isodate
import marshmallow
from dataclasses_json import dataclass_json, LetterCase, Undefined, config

isodatetime_config = config(
    encoder=lambda value: datetime.isoformat(value) if isinstance(value, datetime) else None,
    decoder=lambda value: datetime.fromisoformat(value) if isinstance(value, str) else None,
    mm_field=marshmallow.fields.DateTime(format='iso', allow_none=True)
)

isoduration_config = config(
    encoder=lambda value: isodate.duration_isoformat(value) if isinstance(value, timedelta) else None,
    decoder=lambda value: isodate.parse_duration(value) if isinstance(value, str) else None,
    mm_field=marshmallow.fields.String(allow_none=True)
)


@dataclass_json
@dataclass
class TimeInterval:
    duration: Optional[timedelta] = field(metadata=isoduration_config)
    start: datetime = field(metadata=isodatetime_config)
    end: Optional[datetime] = field(metadata=isodatetime_config)


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class TimeEntry:
    id: str
    user_id: str
    billable: bool
    time_interval: TimeInterval
    workspace_id: str
    project_id: str
    description: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class User:
    id: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Workspace:
    id: str


@dataclass_json
@dataclass
class HourlyRate:
    amount: int
    currency: str


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.EXCLUDE)
@dataclass
class Project:
    id: str
    hourly_rate: HourlyRate

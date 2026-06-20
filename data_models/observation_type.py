from enum import Enum


class ObservationType(str, Enum):
    SNAPSHOT = "snapshot"
    PERIOD = "period"

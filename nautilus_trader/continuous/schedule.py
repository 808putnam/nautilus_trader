from __future__ import annotations

import pandas as pd
import pytz
from msgspec import Meta
from typing import Annotated
import datetime

# An integer constrained to values < 0
NegativeInt = Annotated[int, Meta(lt=0)]

class MarketSchedule:
    def __init__(
        self,
        name: str,
        data: pd.DataFrame,
        timezone: pytz.timezone,
    ):
        self._name = name
        self._zoneinfo = timezone.zone
        self._timezone = timezone

        self._data = data

        # TODO: removes duplicates
        # TODO: check for overlapping times
        # TODO: sort by date and then open time
        # TODO: check open and close are same day
        # TODO: ensure integer index
        # TODO: ensure no missing days, close days have time 00:00 to 00:00
        # TODO: no timezone information before localizing

    def is_open(self, now: pd.Timestamp) -> bool:
        now = now.tz_convert(self._timezone)

        now_time = now.time()

        mask = (
            (now_time >= self._data.open)
            & (now_time < self._data.close)
            & (now.dayofweek == self._data.dayofweek)
        )

        return mask.any()

    def is_closed(self, now: pd.Timestamp) -> bool:
        return not self.is_open(now)

    def next_open(self, now: pd.Timestamp) -> pd.Timestamp | None:
        now = now.tz_convert(self._timezone)

        now_time = now.time()

        dayofweek = now.dayofweek

        sessions = self._data[self._data.dayofweek == dayofweek]
        day_diff = 0

        if not sessions.empty and now_time < sessions.iloc[-1].open:
            open_time = self._data[self._data.open > now_time].iloc[0].open

        else:
            while True:
                dayofweek = (dayofweek + 1) % 7
                day_diff += 1
                if dayofweek not in self._data.dayofweek.values:
                    continue

                sessions = self._data[self._data.dayofweek == dayofweek]
                open_time = sessions.iloc[0].open
                break

        open_day = now.floor("D") + pd.Timedelta(days=day_diff)
        open_timestamp = open_day.replace(hour=open_time.hour, minute=open_time.minute)
        return open_timestamp.tz_convert(pytz.UTC)
    
    def previous_trading_day(self, date: datetime.date, offset: NegativeInt) -> datetime.date:
        
        count = abs(offset)
        
        matched = 0
        while True:
            date -= datetime.timedelta(days=1)
            if date.weekday() in self._data.dayofweek.values:
                matched += 1
            if count == matched:
                break
        return date
                
            
    def time_until_close(self, now: pd.Timestamp) -> pd.Timedelta | None:
        now = now.tz_convert(self._timezone)

        now_time = now.time()

        mask = (
            (now_time >= self._data.open)
            & (now_time < self._data.close)
            & (now.dayofweek == self._data.dayofweek)
        )

        masked = self._data[mask]

        if masked.empty:
            return None  # market closed

        assert len(masked) == 1

        close_time = masked.close.iloc[0]
        close_timestamp = now.floor("D").replace(hour=close_time.hour, minute=close_time.minute)
        return close_timestamp - now

    def __repr__(self) -> str:
        return str(self)

    def __str__(self):
        return f"{type(self).__name__}({self._name})"
    
    def __getstate__(self):
        return (self._name, self._data, self._timezone)
        
    def __setstate__(self, state):
        self._name = state[0]
        self._data = state[1]
        self._timezone = state[2]
    
    def __eq__(self, other: MarketSchedule) -> bool:
        return (
            self._name == other._name,
            self._data.equals(other._data),
            self._timezone == other._timezone,
        )
        
    def to_weekly_calendar_utc(self) -> pd.DataFrame:
        startofweek = pd.Timestamp("2023-11-06")
        df = self._data.copy()
        df["day"] = df["dayofweek"].apply(lambda i: startofweek + pd.Timedelta(days=i))
        df["open"] = df["open"].apply(lambda x: pd.Timedelta(hours=x.hour, minutes=x.minute))
        df["close"] = df["close"].apply(lambda x: pd.Timedelta(hours=x.hour, minutes=x.minute))
        df["open"] = (df["day"] + df["open"]).dt.tz_localize(self._timezone)
        df["close"] = (df["day"] + df["close"]).dt.tz_localize(self._timezone)
        df["name"] = self._name
        df.open = df.open.dt.tz_convert("UTC")
        df.close = df.close.dt.tz_convert("UTC")
        df.dayofweek = df.dayofweek.astype(int)
        return df
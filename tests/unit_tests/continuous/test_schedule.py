from datetime import time

import pandas as pd
import pytz
import pickle
from nautilus_trader.continuous.schedule import MarketSchedule
import datetime

class TestMarketSchedule:
    def setup(self):
        self.data = pd.DataFrame(
            columns=["dayofweek", "open", "close"],
        )

        # Tuesday
        self.data.loc[len(self.data)] = {"dayofweek": 1, "open": time(8, 30), "close": time(16, 0)}
        self.data.loc[len(self.data)] = {"dayofweek": 1, "open": time(16, 30), "close": time(17, 0)}
        self.data.loc[len(self.data)] = {
            "dayofweek": 1,
            "open": time(20, 15),
            "close": time(23, 59),
        }

        # Wednesday
        self.data.loc[len(self.data)] = {"dayofweek": 2, "open": time(8, 30), "close": time(16, 0)}

        # Thursday
        self.data.loc[len(self.data)] = {"dayofweek": 3, "open": time(8, 30), "close": time(16, 0)}

        # Saturday
        self.data.loc[len(self.data)] = {"dayofweek": 5, "open": time(17, 0), "close": time(23, 59)}
    
    def test_schedule_previous_trading_day(self):
        
        calendar = MarketSchedule(name="test", data=self.data, timezone=pytz.UTC)
        
        now_day = datetime.date(2024, 1, 27)  # Saturday
        expected = datetime.date(2024, 1, 25)  # Thursday
        assert calendar.previous_trading_day(date=now_day, offset=-1) == expected
        
        now_day = datetime.date(2024, 1, 23)  # Tuesday
        expected = datetime.date(2024, 1, 20)  # Saturday
        assert calendar.previous_trading_day(date=now_day, offset=-1) == expected
        
        now_day = datetime.date(2024, 1, 25)  # Thursday
        expected = datetime.date(2024, 1, 24)  # Wedsnesday
        assert calendar.previous_trading_day(date=now_day, offset=-1) == expected
        
        now_day = datetime.date(2024, 1, 26)  # Friday
        expected = datetime.date(2024, 1, 25)  # Thursday
        assert calendar.previous_trading_day(date=now_day, offset=-1) == expected
        
    def test_is_open_utc(self):
        calendar = MarketSchedule(name="test", data=self.data, timezone=pytz.UTC)

        assert not calendar.is_open(pd.Timestamp("1980-01-01 08:29:00", tz="UTC"))  # Tuesday
        assert calendar.is_open(pd.Timestamp("1980-01-01 08:30:00", tz="UTC"))  # Tuesday

        assert not calendar.is_open(pd.Timestamp("1980-01-04 08:30:00", tz="UTC"))  # Friday
        assert calendar.is_open(pd.Timestamp("1980-01-01 15:59:00", tz="UTC"))  # Tuesday
        assert not calendar.is_open(pd.Timestamp("1980-01-01 16:00:00", tz="UTC"))  # Tuesday

        assert not calendar.is_open(pd.Timestamp("1980-01-01 16:29:00", tz="UTC"))  # Tuesday
        assert calendar.is_open(pd.Timestamp("1980-01-01 16:30:00", tz="UTC"))  # Tuesday

        assert calendar.is_open(pd.Timestamp("1980-01-01 16:59:00", tz="UTC"))  # Tuesday
        assert not calendar.is_open(pd.Timestamp("1980-01-01 17:00:00", tz="UTC"))  # Tuesday

        assert calendar.is_open(pd.Timestamp("1980-01-01 20:15:00", tz="UTC"))  # Tuesday
        assert not calendar.is_open(pd.Timestamp("1980-01-01 20:14:00", tz="UTC"))  # Tuesday

    def test_is_open_with_timezone(self):
        calendar = MarketSchedule(
            name="test",
            data=self.data,
            timezone=pytz.timezone("America/Chicago"),
        )

        assert calendar.is_open(pd.Timestamp("2023-10-28 02:00:00", tz="UTC"))  # Saturday

        assert not calendar.is_open(pd.Timestamp("1980-01-01 14:29:00", tz="UTC"))  # Tuesday
        assert calendar.is_open(pd.Timestamp("1980-01-01 14:30:00", tz="UTC"))  # Tuesday

        assert calendar.is_open(pd.Timestamp("1980-01-01 21:59:00", tz="UTC"))  # Tuesday
        assert not calendar.is_open(pd.Timestamp("1980-01-01 22:00:00", tz="UTC"))  # Tuesday

    def test_next_open_utc(self):
        calendar = MarketSchedule(name="test", data=self.data, timezone=pytz.UTC)

        # Thursday > Saturday
        assert calendar.next_open(pd.Timestamp("1980-01-03 08:30", tz="UTC")) == pd.Timestamp(
            "1980-01-05 17:00",
            tz="UTC",
        )

        # Tuesday before first session
        assert calendar.next_open(pd.Timestamp("1980-01-01 08:29", tz="UTC")) == pd.Timestamp(
            "1980-01-01 08:30",
            tz="UTC",
        )

        # Tuesday in first session
        assert calendar.next_open(pd.Timestamp("1980-01-01 08:30", tz="UTC")) == pd.Timestamp(
            "1980-01-01 16:30",
            tz="UTC",
        )

        # Tuesday before second session
        assert calendar.next_open(pd.Timestamp("1980-01-01 16:29", tz="UTC")) == pd.Timestamp(
            "1980-01-01 16:30",
            tz="UTC",
        )

        # Tuesday in second session
        assert calendar.next_open(pd.Timestamp("1980-01-01 16:30", tz="UTC")) == pd.Timestamp(
            "1980-01-01 20:15",
            tz="UTC",
        )

        # Tuesday before third session
        assert calendar.next_open(pd.Timestamp("1980-01-01 20:14", tz="UTC")) == pd.Timestamp(
            "1980-01-01 20:15",
            tz="UTC",
        )

        # Tuesday in third session
        assert calendar.next_open(pd.Timestamp("1980-01-01 20:15", tz="UTC")) == pd.Timestamp(
            "1980-01-02 08:30",
            tz="UTC",
        )

        # Thursday > Thursday
        assert calendar.next_open(pd.Timestamp("1980-01-03 08:29", tz="UTC")) == pd.Timestamp(
            "1980-01-03 08:30",
            tz="UTC",
        )

        # Friday (closed) > Saturday
        assert calendar.next_open(pd.Timestamp("1980-01-04 08:29", tz="UTC")) == pd.Timestamp(
            "1980-01-05 17:00",
            tz="UTC",
        )

    def test_next_open_with_timezone(self):
        pass

    def test_time_until_close(self):
        calendar = MarketSchedule(name="test", data=self.data, timezone=pytz.UTC)

        # tuesday
        assert calendar.time_until_close(
            pd.Timestamp("1980-01-01 15:59:00", tz="UTC"),
        ) == pd.Timedelta(minutes=1)
        assert calendar.time_until_close(pd.Timestamp("1980-01-01 16:00:00", tz="UTC")) is None

        assert calendar.time_until_close(pd.Timestamp("1980-01-01 16:29:00", tz="UTC")) is None
        assert calendar.time_until_close(
            pd.Timestamp("1980-01-01 16:30:00", tz="UTC"),
        ) == pd.Timedelta(minutes=30)

        # friday (closed)
        assert calendar.time_until_close(pd.Timestamp("1980-01-04 16:00:00", tz="UTC")) is None

        # weds
        assert calendar.time_until_close(
            pd.Timestamp("1980-01-02 08:30:00", tz="UTC"),
        ) == pd.Timedelta("0 days 07:30:00")
    
    def test_equality(self):
        schedule = MarketSchedule(name="test", data=self.data, timezone=pytz.UTC)
        assert schedule == schedule
        
    def test_schedule_pickle(self):
        
        # Arrange
        schedule = MarketSchedule(name="test", data=self.data, timezone=pytz.UTC)
        
        # Act
        pickled = pickle.dumps(schedule)
        unpickled = pickle.loads(pickled)  # noqa S301 (pickle is safe here)
        
        # Assert
        assert unpickled == schedule
import pandas as pd
import psycopg2.extras as pextra

import instrument_master.common.data.types as icdtyp
import instrument_master.common.sql_writer_backend as icsqlw


class IbSqlWriterBackend(icsqlw.AbstractSqlWriterBackend):
    """
    Manager of CRUD operations on a database defined in db.sql.
    """

    FREQ_ATTR_MAPPING = {
        icdtyp.Frequency.Daily: {
            "table_name": "IbDailyData",
            "datetime_field_name": "date",
        },
        icdtyp.Frequency.Minutely: {
            "table_name": "IbMinuteData",
            "datetime_field_name": "datetime",
        },
        icdtyp.Frequency.Tick: {
            "table_name": "IbTickData",
            "datetime_field_name": "datetime",
        },
    }

    def insert_bulk_daily_data(
        self,
        df: pd.DataFrame,
    ) -> None:
        """
        Insert daily data for a particular TradeSymbol entry in bulk.

        :param df: a dataframe from s3
        """
        with self.conn:
            with self.conn.cursor() as curs:
                pextra.execute_values(
                    curs,
                    "INSERT INTO IbDailyData "
                    "(trade_symbol_id, date, open, high, low, close, volume, average, barCount) "
                    "VALUES %s ON CONFLICT DO NOTHING",
                    df.to_dict("records"),
                    template="(%(trade_symbol_id)s, %(date)s, %(open)s,"
                    " %(high)s, %(low)s, %(close)s, %(volume)s, %(average)s, %(barCount)s)",
                )

    def insert_daily_data(
        self,
        trade_symbol_id: int,
        date: str,
        open_val: float,
        high_val: float,
        low_val: float,
        close_val: float,
        volume_val: int,
        average_val: float,
        bar_count_val: int,
    ) -> None:
        """
        Insert daily data for a particular TradeSymbol entry.

        :param trade_symbol_id: id of TradeSymbol
        :param date: date string
        :param open_val: open price
        :param high_val: high price
        :param low_val: low price
        :param close_val: close price
        :param volume_val: volume
        :param average_val: average
        :param bar_count_val: bar count
        """
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(
                    "INSERT INTO IbDailyData "
                    "(trade_symbol_id, date, open, high, low, close, volume, average, barCount) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    [
                        trade_symbol_id,
                        date,
                        open_val,
                        high_val,
                        low_val,
                        close_val,
                        volume_val,
                        average_val,
                        bar_count_val,
                    ],
                )

    def insert_bulk_minute_data(
        self,
        df: pd.DataFrame,
    ) -> None:
        """
        Insert minute data for a particular TradeSymbol entry in bulk.

        :param df: a dataframe from s3
        """
        with self.conn:
            with self.conn.cursor() as curs:
                pextra.execute_values(
                    curs,
                    "INSERT INTO IbMinuteData "
                    "(trade_symbol_id, datetime, open, high, low, close, "
                    "volume, average, barCount) "
                    "VALUES %s ON CONFLICT DO NOTHING",
                    df.to_dict("records"),
                    template="(%(trade_symbol_id)s, %(datetime)s, %(open)s,"
                    " %(high)s, %(low)s, %(close)s, %(volume)s, %(average)s, %(barCount)s)",
                )

    def insert_minute_data(
        self,
        trade_symbol_id: int,
        date_time: str,
        open_val: float,
        high_val: float,
        low_val: float,
        close_val: float,
        volume_val: int,
        average_val: float,
        bar_count_val: int,
    ) -> None:
        """
        Insert minute data for a particular TradeSymbol entry.

        :param trade_symbol_id: id of TradeSymbol
        :param date_time: date and time string
        :param open_val: open price
        :param high_val: high price
        :param low_val: low price
        :param close_val: close price
        :param volume_val: volume
        :param average_val: average
        :param bar_count_val: bar count
        """
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(
                    "INSERT INTO IbMinuteData "
                    "(trade_symbol_id, datetime, open, high, low, close, "
                    "volume, average, barCount) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    [
                        trade_symbol_id,
                        date_time,
                        open_val,
                        high_val,
                        low_val,
                        close_val,
                        volume_val,
                        average_val,
                        bar_count_val,
                    ],
                )

    def insert_tick_data(
        self,
        trade_symbol_id: int,
        date_time: str,
        price_val: float,
        size_val: int,
    ) -> None:
        """
        Insert tick data for a particular TradeSymbol entry.

        :param trade_symbol_id: id of TradeSymbol
        :param date_time: date and time string
        :param price_val: price of the transaction
        :param size_val: size of the transaction
        """
        with self.conn:
            with self.conn.cursor() as curs:
                curs.execute(
                    "INSERT INTO IbTickData "
                    "(trade_symbol_id, datetime, price, size) "
                    "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                    [
                        trade_symbol_id,
                        date_time,
                        price_val,
                        size_val,
                    ],
                )

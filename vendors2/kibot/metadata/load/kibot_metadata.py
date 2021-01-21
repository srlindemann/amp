import abc
import os
import re
from typing import Any, List, Tuple, Optional, Type, Union

import pandas as pd
import helpers.dbg as dbg
import helpers.csv as csv

import vendors2.kibot.metadata.load.expiry_contract_mapper as vkmlex
import vendors2.kibot.data.load.s3_data_loader as vkdls3
import vendors2.kibot.metadata.load.s3_backend as vkmls3
import vendors2.kibot.metadata.load.expiry_contract_mapper as vkmdle
import vendors2.kibot.data.types as vkdt
import vendors2.kibot.metadata.types as vkmdt


class KibotMetadata:
    # pylint: disable=line-too-long
    """
    Generate Kibot metadata.

    The metadata is computed from:
     - minutely contract metadata (`read_1min_contract_metadata()`)
     - tick-bid-ask metadata (`read_continuous_contract_metadata()`) is used to
       extract start date and exchange, which are not available in the minutely
       metadata.

    The expiration dates provided here are accurate for both daily and minutely
    metadata.

    The metadata is indexed by the symbol.

    The metadata contains the following columns:
    - `Description`
    - `StartDate`
    - `Exchange`
    - `num_contracts`
    - `min_contract`
    - `max_contract`
    - `num_expiries`
    - `expiries`

                                   Description  StartDate                                  Exchange  num_contracts min_contract max_contract  num_expiries                                expiries
    AD   CONTINUOUS AUSTRALIAN DOLLAR CONTRACT  9/27/2009  Chicago Mercantile Exchange (CME GLOBEX)           65.0      11.2009      11.2020          12.0  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    AEX          CONTINUOUS AEX INDEX CONTRACT        NaN                                       NaN          116.0      03.2010      02.2020          12.0  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    """
    # pylint: enable=line-too-long

    def __init__(self) -> None:
        self.minutely_metadata = self._compute_kibot_metadata("1min")
        self.tickbidask_metadata = self._compute_kibot_metadata("tick-bid-ask")

    def get_metadata(self, contract_type: str = "1min") -> pd.DataFrame:
        """
        Return the metadata.
        """
        if contract_type in ["1min", "daily"]:
            # Minutely and daily dataframes are identical except for the `Link`
            # column.
            metadata = self.minutely_metadata.copy()
        elif contract_type == "tick-bid-ask":
            metadata = self.tickbidask_metadata.copy()
        else:
            raise ValueError("Invalid `contract_type`='%s'" % contract_type)
        return metadata

    def get_futures(self, contract_type: str = "1min") -> List[str]:
        """
        Return the continuous contracts, e.g., ES, CL.
        """
        futures: List[str] = self.get_metadata(contract_type).index.tolist()
        return futures

    @classmethod
    # For now the metadata is always stored on S3, so we don't need to use `cls`.
    def get_expiry_contracts(cls, symbol: str) -> List[str]:
        """
        Return the expiry contracts corresponding to a continuous contract.
        """
        one_min_contract_metadata = cls.read_1min_contract_metadata()
        one_min_contract_metadata, _ = cls._extract_month_year_expiry(
            one_min_contract_metadata
        )
        # Select the rows with the Symbol equal to the requested one.
        mask = one_min_contract_metadata["SymbolBase"] == symbol
        df = one_min_contract_metadata[mask]
        contracts: List[str] = df.loc[:, "Symbol"].tolist()
        return contracts

    @classmethod
    def read_tickbidask_contract_metadata(cls) -> pd.DataFrame:
        return vkmls3.S3Backend().read_tickbidask_contract_metadata()

    @classmethod
    def read_kibot_exchange_mapping(cls) -> pd.DataFrame:
        return vkmls3.S3Backend().read_kibot_exchange_mapping()

    @classmethod
    def read_continuous_contract_metadata(cls) -> pd.DataFrame:
        return vkmls3.S3Backend().read_continuous_contract_metadata()

    @classmethod
    def read_1min_contract_metadata(cls) -> pd.DataFrame:
        return vkmls3.S3Backend().read_1min_contract_metadata()

    # //////////////////////////////////////////////////////////////////////////

    # TODO(Julia): Replace `one_min` with `expiry` once the PR is approved.
    @classmethod
    def _compute_kibot_metadata(cls, contract_type: str) -> pd.DataFrame:
        if contract_type in ["1min", "daily"]:
            # Minutely and daily dataframes are identical except for the `Link`
            # column.
            one_min_contract_metadata = cls.read_1min_contract_metadata()
        elif contract_type == "tick-bid-ask":
            one_min_contract_metadata = (
                cls.read_tickbidask_contract_metadata()
            )
        else:
            raise ValueError("Invalid `contract_type`='%s'" % contract_type)
        continuous_contract_metadata = (
            cls.read_continuous_contract_metadata()
        )
        # Extract month, year, expiries and SymbolBase from the Symbol col.
        (
            one_min_contract_metadata,
            one_min_symbols_metadata,
        ) = cls._extract_month_year_expiry(one_min_contract_metadata)
        # Calculate stats for expiries.
        expiry_counts = cls._calculate_expiry_counts(
            one_min_contract_metadata
        )
        # Drop unneeded columns from the symbol metadata dataframe
        # originating from 1 min contract metadata.
        one_min_contracts = one_min_symbols_metadata.copy()
        one_min_contracts.set_index("Symbol", inplace=True)
        one_min_contracts.drop(
            columns=["year", "Link"], inplace=True, errors="ignore"
        )
        # Choose needed columns from the continuous contract metadata.
        cont_contracts_chosen = continuous_contract_metadata.loc[
                                :, ["Symbol", "StartDate", "Exchange"]
                                ]
        cont_contracts_chosen = cont_contracts_chosen.set_index(
            "Symbol", drop=True
        )
        # Combine 1 min metadata, continuous contract metadata and stats for
        # expiry contracts.
        if contract_type == "tick-bid-ask":
            to_concat = [one_min_contracts, expiry_counts]
        else:
            to_concat = [one_min_contracts, cont_contracts_chosen, expiry_counts]
        kibot_metadata = pd.concat(
            to_concat,
            axis=1,
            join="outer",
            sort=True,
        )
        # Sort by index.
        kibot_metadata.sort_index(inplace=True)
        # Remove empty nans.
        kibot_metadata.dropna(how="all", inplace=True)
        # Convert date columns to datetime.
        kibot_metadata["min_contract"] = pd.to_datetime(
            kibot_metadata["min_contract"], format="%m.%Y"
        )
        kibot_metadata["max_contract"] = pd.to_datetime(
            kibot_metadata["max_contract"], format="%m.%Y"
        )
        # Data can be incomplete, when mocked in a testing environment.
        kibot_metadata = kibot_metadata[kibot_metadata["num_contracts"].notna()]
        # Convert integer columns to `int`.
        kibot_metadata["num_contracts"] = kibot_metadata["num_contracts"].astype(
            int
        )
        kibot_metadata["num_expiries"] = kibot_metadata["num_expiries"].astype(
            int
        )
        # Append Exchange_symbol, Exchange_group, Globex_symbol columns.
        kibot_metadata = cls._annotate_with_exchange_mapping(
            kibot_metadata
        )
        # Change index to continuous.
        kibot_metadata = kibot_metadata.reset_index()
        kibot_metadata = kibot_metadata.rename({"index": "Kibot_symbol"}, axis=1)
        columns = [
            "Kibot_symbol",
            "Description",
            "StartDate",
            "Exchange",
            "Exchange_group",
            "Exchange_abbreviation",
            "Exchange_symbol",
            "num_contracts",
            "min_contract",
            "max_contract",
            "num_expiries",
            "expiries",
        ]
        return kibot_metadata[columns]

    _CONTRACT_EXPIRIES = {
        "F": 1,
        "G": 2,
        "H": 3,
        "J": 4,
        "K": 5,
        "M": 6,
        "N": 7,
        "Q": 8,
        "U": 9,
        "V": 10,
        "X": 11,
        "Z": 12,
    }

    @classmethod
    def _get_zero_elememt(cls, list_: List[Any]) -> Any:
        return list_[0] if list_ else None

    @classmethod
    def _extract_month_year_expiry(cls,
            one_min_contract_metadata: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract month, year, expiries and SymbolBase from the Symbol.
        """
        # Extract year by extracting the trailing digits. Contracts that
        # do not have a year are continuous.
        one_min_contract_metadata = one_min_contract_metadata.copy()
        one_min_contract_metadata["year"] = (
            one_min_contract_metadata["Symbol"]
                .apply(lambda x: re.findall(r"\d+$", x))
                .apply(cls._get_zero_elememt)
        )
        one_min_symbols_metadata = one_min_contract_metadata.loc[
            one_min_contract_metadata["year"].isna()
        ]
        # Drop continuous contracts.
        one_min_contract_metadata.dropna(subset=["year"], inplace=True)
        # Extract SymbolBase, month, year and expiries from contract names.
        symbol_month_year = (
            one_min_contract_metadata["Symbol"]
                .apply(vkmlex.ExpiryContractMapper.parse_expiry_contract)
                .apply(pd.Series)
        )
        symbol_month_year.columns = ["SymbolBase", "month", "year"]
        symbol_month_year["expiries"] = (
                symbol_month_year["month"] + symbol_month_year["year"]
        )
        symbol_month_year.drop(columns="year", inplace=True)
        one_min_contract_metadata.drop(
            columns="SymbolBase", inplace=True, errors="ignore"
        )
        one_min_contract_metadata = pd.concat(
            [one_min_contract_metadata, symbol_month_year], axis=1
        )
        return one_min_contract_metadata, one_min_symbols_metadata

    @classmethod
    def _calculate_expiry_counts(cls,
            one_min_contract_metadata: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate the following stats for each symbol:

        - number of contracts
        - number of expiries
        - the oldest contract
        - the newest contract

        :return: pd.DataFrame with calculated counts
        """
        one_min_contracts_with_exp = one_min_contract_metadata.copy()
        # To sort the contracts easily, revert expiries so that the year
        # comes before month.
        one_min_contracts_with_exp[
            "expiries_year_first"
        ] = one_min_contracts_with_exp["expiries"].apply(lambda x: x[1:] + x[0])
        base_groupby = one_min_contracts_with_exp.groupby("SymbolBase")
        # Count the contracts.
        num_contracts = pd.Series(
            base_groupby["expiries"].nunique(), name="num_contracts"
        )
        # Get months at which the contract expires.
        num_expiries = pd.Series(
            base_groupby["month"].nunique(), name="num_expiries"
        )
        # Get the earliest contract, bring it to the mm.yyyy format.
        min_contract = pd.Series(
            base_groupby["expiries_year_first"].min(), name="min_contract"
        )
        min_contract = min_contract.apply(
            lambda x: str(cls._CONTRACT_EXPIRIES[x[-1]]).zfill(2)
                      + ".20"
                      + x[:2]
        )
        # Get the oldest contract, bring it to the mm.yyyy format.
        max_contract = pd.Series(
            base_groupby["expiries_year_first"].max(), name="max_contract"
        )
        max_contract = max_contract.apply(
            lambda x: str(cls._CONTRACT_EXPIRIES[x[-1]]).zfill(2)
                      + ".20"
                      + x[:2]
        )
        # Get all months at which contracts for each symbol expires,
        # change the str months to the month numbers from 0 to 11.
        expiries = pd.Series(base_groupby["month"].unique(), name="expiries")
        expiries = expiries.apply(
            lambda x: list(map(lambda y: cls._CONTRACT_EXPIRIES[y], x))
        )
        # Combine all counts.
        expiry_counts = pd.concat(
            [num_contracts, min_contract, max_contract, num_expiries, expiries],
            axis=1,
        )
        return expiry_counts

    @classmethod
    def _annotate_with_exchange_mapping(cls,
            kibot_metadata: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Annotate Kibot with exchanges and their symbols.

        The annotations include
         - "Exchange_group" for high-level exchanges' group
         - "Exchange_abbreviation" for exchange abbreviation
         - "Exchange_symbol" for contract designation in given exchange

        Annotations are provided only for commodity-related contracts.

        :param kibot_metadata: Kibot metadata dataframe
        kibot_to_cme_mapping = (
            vkmls3.S3Backend().read_kibot_exchange_mapping()
        )
        """
        kibot_to_cme_mapping = cls.read_kibot_exchange_mapping()
        # Add mapping columns to the dataframe.
        annotated_metadata = pd.concat(
            [kibot_metadata, kibot_to_cme_mapping], axis=1
        )
        return annotated_metadata

    def get_kibot_symbols(self, contract_type: str = "1min") -> pd.Series:
        metadata = self.get_metadata(contract_type)
        return metadata['Kibot_symbol']


class ContractLifetimeComputer(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def compute_lifetime(contract_name: str) -> vkmdt.ContractLifetime:
        """Compute the lifetime of a contract, e.g. 'CLJ17'.

        :param contract_name: the contract for which to compute the lifetime.
        :return: the computed lifetime.
        """


class KibotTradingActivityContractLifetimeComputer(ContractLifetimeComputer):
    """Use the price data from Kibot to compute the lifetime."""

    @staticmethod
    def compute_lifetime(contract_name: str) -> vkmdt.ContractLifetime:
        df = vkdls3.S3KibotDataLoader() \
            .read_data("Kibot", contract_name,
                       vkdt.AssetClass.Futures, vkdt.Frequency.Daily,
                       vkdt.ContractType.Expiry)
        start_date = pd.Timestamp(df.first_valid_index())
        end_date = pd.Timestamp(df.last_valid_index())
        return vkmdt.ContractLifetime(start_date, end_date)


class ContractsLoader:
    def __init__(self, symbols: List[str], file: str, lifetime_computer: ContractLifetimeComputer, refresh: bool = False) -> None:
        if os.path.isfile(file) and not refresh:
            self.contracts = self._load_from_csv(file)
        else:
            self.contracts = self._compute_lifetimes(symbols, lifetime_computer)
            csv.to_typed_csv(self.contracts, file)

    def get_contracts(self):
        return self.contracts

    @staticmethod
    def _load_from_csv(file: str) -> pd.DataFrame:
        return csv.from_typed_csv(file)

    @staticmethod
    def _compute_lifetimes(symbols: Union[pd.Series, List[str]], lifetime_computer: ContractLifetimeComputer) -> pd.DataFrame:
        """Compute the lifetime for all contracts available for all symbols passed in.

        :param symbols: kibot symbols from which to retrieve contracts
        """
        kb = KibotMetadata()
        dbg.dassert_in(type(symbols), [pd.Series, list])
        if isinstance(symbols, pd.Series):
            symbols = [symbol for _, symbol in symbols.items()]

        df = []
        for symbol in symbols:
            contracts = kb.get_expiry_contracts(symbol)
            lifetimes = [lifetime_computer.compute_lifetime(cn) for cn in contracts]
            for contract, lifetime in zip(contracts, lifetimes):
                lifetime.start_date = pd.Timestamp(lifetime.start_date)
                lifetime.end_date = pd.Timestamp(lifetime.end_date)
                df.append([symbol, contract, lifetime.start_date, lifetime.end_date])
        return pd.DataFrame(df, columns=["symbol", "contract", "start_date", "end_date"])


class ContractExpiryMapper:
    def __init__(self, contracts_factory: ContractsLoader) -> None:
        self.contracts = contracts_factory.get_contracts()

    def get_expiry(self, date: vkmdt.DATE_TYPE, date_month_offset: int, symbol: str) -> Optional[vkmdt.Expiry]:
        """Return expiry for contract given `datetime` and `month` offset.

        :param date: includes year, month, day, and possibly time (otherwise ... assumed)
        :param date_month_offset: relative month, e.g., 1 for front month, 2 for first back month, and so on
        :param symbol: Kibot symbol
        :return: absolute month and year of contract for `symbol`, expressed using Futures month codes
            and last two digits of year, e.g., `("Z", "20")`
        """
        dbg.dassert_in(symbol, self.contracts['symbol'].values)

        # Grab all contract lifetimes.
        contracts = self.contracts.loc[self.contracts['symbol'] == symbol]
        df = contracts.sort_values(by="end_date")

        # Find first index with a `start_date` before `date` and
        # an `end_date` after `date`.
        idx = df['end_date'].searchsorted(pd.Timestamp(date), side='left')
        while df['start_date'].iloc[idx] > date:
            idx = df['end_date'].searchsorted(pd.Timestamp(date), side='left')
            # 0 = no contracts with a `start_date` before `date`
            if idx >= len(df.index) or idx == 0:
                return None

        # Add the offset.
        idx = idx + date_month_offset
        if idx >= len(df.index):
            # Index does not exist.
            return None

        # Return the expiry date.
        ret = df['end_date'][idx]
        return vkmdt.Expiry(
            month=vkmdle.ExpiryContractMapper().month_to_expiry_num(ret.month),
            year=str(ret.year)[2::]
        )


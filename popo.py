import datetime
import re
from decimal import Decimal
from numbers import Real
from typing import Optional, Union

from inflection import humanize
from pydantic import BaseModel
from pydantic.class_validators import root_validator, validator
from pydantic.fields import Field
from web3 import Web3
from web3.types import Address, ChecksumAddress


def is_positive_number(value: Real):
    if value < Decimal(0):
        raise ValueError("Expected a positive value")
    return value







class Token(BaseModel):
    address: Union[Address, ChecksumAddress, str] = ""

    @validator("address")
    def check_address(cls, value: Union[Address, ChecksumAddress, str]):
        if isinstance(value, bytes):
            value = value.decode()
        if re.match(r"^0x\w+", value) is None:  # type: ignore
            raise ValueError(f"'{value}' is not a valid contract address")  # type: ignore
        return Web3.toChecksumAddress(value)


class Platform(BaseModel):
    network: Optional[str]

    @validator("network")
    def check_platform(cls, value: str):
        value = value.upper()
        if value and value not in ("BSC", "ETH", "MATIC", "COINBASE"):
            raise ValueError("Invalid network. Expected one of eth|bsc|matic")
        return value


class Coin(Token, Platform):
    symbol: str = ""

    @validator("symbol")
    def symbol_is_alphanumeric(cls, value: str):
        if not value.isalnum():
            raise ValueError(f"{value} is not a valid symbol")
        return value




import pytest
from brownie_tokens import MintableForkToken


COINS = [
    "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # usdt
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # wbtc
    "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # weth
]


@pytest.fixture(scope="session")
def alice(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def bob(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def charlie(accounts):
    return accounts[2]


@pytest.fixture(scope="module")
def coins():
    return [MintableForkToken(addr) for addr in COINS]


@pytest.fixture(scope="module")
def decimals():
    return [6, 8, 18]


@pytest.fixture(scope="module")
def crypto_zap(alice, DepositZap):
    return DepositZap.deploy(
        "0x80466c64868E1ab14a1Ddf27A676C3fcBE638Fe5", {"from": alice}
    )


@pytest.fixture(scope="module")
def crypto_lp_token(CurveTokenV4):
    return CurveTokenV4.at("0xcA3d75aC011BF5aD07a98d02f18225F9bD9A6BDF")


@pytest.fixture(scope="module", autouse=True)
def pre_mining(alice, crypto_zap, coins, decimals):
    """Mint a bunch of test tokens"""
    for coin, decimal in zip(coins, decimals):
        coin._mint_for_testing(alice, 100_000 * 10 ** decimal)
        coin.approve(crypto_zap, 2 ** 256 - 1, {"from": alice})

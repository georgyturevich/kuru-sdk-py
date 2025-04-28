import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from web3 import Web3
from web3.exceptions import ContractLogicError

from kuru_sdk.token import Token, TokenError

# --- Constants ---
MOCK_CONTRACT_ADDRESS = "0x1234567890123456789012345678901234567890"
MOCK_USER_ADDRESS = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
MOCK_SPENDER_ADDRESS = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
MOCK_PRIVATE_KEY = "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
MOCK_TX_HASH = "0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"

# --- Fixtures ---

@pytest.fixture
def mock_web3():
    """Fixture for a mocked Web3 instance."""
    mock = MagicMock(spec=Web3)
    mock.eth = MagicMock()
    mock.eth.contract = MagicMock()
    mock.eth.account = MagicMock()
    mock.eth.get_transaction_count = MagicMock(return_value=1)
    mock.eth.max_priority_fee = 10**9 # Example gwei value
    # Make sure address conversion works
    mock.to_checksum_address = Web3.to_checksum_address
    return mock

@pytest.fixture
def mock_contract(mock_web3):
    """Fixture for a mocked Contract instance."""
    mock = MagicMock()
    mock.functions = MagicMock()
    mock.address = Web3.to_checksum_address(MOCK_CONTRACT_ADDRESS)
    mock_web3.eth.contract.return_value = mock
    return mock

@pytest.fixture
@patch("builtins.open", new_callable=MagicMock)
@patch("json.load", return_value=[]) # Minimal valid ABI
def token_instance(mock_json_load, mock_open, mock_web3):
    """Fixture for a Token instance with mocked web3 and ABI loading."""
    return Token(
        web3=mock_web3,
        contract_address=MOCK_CONTRACT_ADDRESS,
        private_key=MOCK_PRIVATE_KEY
    )

@pytest.fixture
@patch("builtins.open", new_callable=MagicMock)
@patch("json.load", return_value=[]) # Minimal valid ABI
def token_instance_no_pk(mock_json_load, mock_open, mock_web3):
    """Fixture for a Token instance without a private key."""
    return Token(
        web3=mock_web3,
        contract_address=MOCK_CONTRACT_ADDRESS,
        private_key=None
    )

# --- Test Cases ---

def test_token_initialization(token_instance, mock_web3, mock_contract):
    """Test successful initialization and ABI loading."""
    assert token_instance.web3 == mock_web3
    assert token_instance.contract_address == Web3.to_checksum_address(MOCK_CONTRACT_ADDRESS)
    assert token_instance.private_key == MOCK_PRIVATE_KEY
    mock_web3.eth.contract.assert_called_once_with(
        address=Web3.to_checksum_address(MOCK_CONTRACT_ADDRESS),
        abi=[]
    )
    assert token_instance.contract == mock_contract
    assert token_instance._name is None
    assert token_instance._symbol is None
    assert token_instance._decimals is None

def test_token_metadata_properties(token_instance, mock_contract):
    """Test fetching token metadata properties (name, symbol, decimals)."""
    # Setup mock return values
    mock_contract.functions.name().call.return_value = "MockToken"
    mock_contract.functions.symbol().call.return_value = "MCK"
    mock_contract.functions.decimals().call.return_value = 18

    # Access properties
    assert token_instance.name == "MockToken"
    assert token_instance.symbol == "MCK"
    assert token_instance.decimals == 18

    # Check caching
    assert token_instance._name == "MockToken"
    assert token_instance._symbol == "MCK"
    assert token_instance._decimals == 18

    # Ensure call() was called only once for each due to caching
    mock_contract.functions.name().call.assert_called_once()
    mock_contract.functions.symbol().call.assert_called_once()
    mock_contract.functions.decimals().call.assert_called_once()

    # Access again, should use cache
    assert token_instance.name == "MockToken"
    mock_contract.functions.name().call.assert_called_once() # Still once

def test_format_units(token_instance, mock_contract):
    """Test converting raw units to decimal representation."""
    mock_contract.functions.decimals().call.return_value = 6 # e.g., USDC
    amount_raw = 123456789
    expected_decimal = Decimal("123.456789")
    assert token_instance.format_units(amount_raw) == expected_decimal

def test_format_units_18_decimals(token_instance, mock_contract):
    """Test converting raw units with 18 decimals."""
    mock_contract.functions.decimals().call.return_value = 18
    amount_raw = 5 * (10**18) # 5 tokens
    expected_decimal = Decimal("5.0")
    assert token_instance.format_units(amount_raw) == expected_decimal

def test_parse_units(token_instance, mock_contract):
    """Test converting decimal representation to raw units."""
    mock_contract.functions.decimals().call.return_value = 6
    amount_decimal = "123.456789"
    expected_raw = 123456789
    assert token_instance.parse_units(amount_decimal) == expected_raw

def test_parse_units_18_decimals(token_instance, mock_contract):
    """Test converting decimal with 18 decimals."""
    mock_contract.functions.decimals().call.return_value = 18
    amount_decimal = "5.0"
    expected_raw = 5 * (10**18)
    assert token_instance.parse_units(amount_decimal) == expected_raw

def test_balance_of(token_instance, mock_contract):
    """Test fetching token balance."""
    expected_balance = 500 * (10**18)
    mock_contract.functions.balanceOf(Web3.to_checksum_address(MOCK_USER_ADDRESS)).call.return_value = expected_balance

    balance = token_instance.balance_of(MOCK_USER_ADDRESS)
    assert balance == expected_balance
    mock_contract.functions.balanceOf(Web3.to_checksum_address(MOCK_USER_ADDRESS)).call.assert_called_once()

def test_allowance(token_instance, mock_contract):
    """Test fetching token allowance."""
    expected_allowance = 1000 * (10**18)
    mock_contract.functions.allowance(
        Web3.to_checksum_address(MOCK_USER_ADDRESS),
        Web3.to_checksum_address(MOCK_SPENDER_ADDRESS)
    ).call.return_value = expected_allowance

    allowance = token_instance.allowance(MOCK_USER_ADDRESS, MOCK_SPENDER_ADDRESS)
    assert allowance == expected_allowance
    mock_contract.functions.allowance(
        Web3.to_checksum_address(MOCK_USER_ADDRESS),
        Web3.to_checksum_address(MOCK_SPENDER_ADDRESS)
    ).call.assert_called_once()


def test_approve_with_private_key(token_instance, mock_web3, mock_contract):
    """Test approving spender with a private key (local signing)."""
    amount_raw = 100 * (10**18)
    mock_tx = MagicMock() # Mock transaction object returned by contract.functions.approve()
    mock_contract.functions.approve(
        Web3.to_checksum_address(MOCK_SPENDER_ADDRESS),
        amount_raw
    ).return_value = mock_tx # Important: return the tx mock here

    # Mock estimate_gas
    mock_tx.estimate_gas.return_value = 50000

    # Mock build_transaction
    raw_tx_dict = {'data': '0x...', 'nonce': 1, 'gas': 50000}
    mock_tx.build_transaction.return_value = raw_tx_dict

    # Mock sign_transaction
    signed_tx_mock = MagicMock()
    signed_tx_mock.raw_transaction = b'signed_tx_bytes'
    mock_web3.eth.account.sign_transaction.return_value = signed_tx_mock

    # Mock send_raw_transaction
    mock_web3.eth.send_raw_transaction.return_value = bytes.fromhex(MOCK_TX_HASH[2:])

    tx_hash = token_instance.approve(MOCK_SPENDER_ADDRESS, amount_raw, MOCK_USER_ADDRESS)

    assert tx_hash == MOCK_TX_HASH

    # Verify calls
    mock_web3.eth.get_transaction_count.assert_called_once_with(Web3.to_checksum_address(MOCK_USER_ADDRESS))
    mock_contract.functions.approve.assert_called_once_with(
        Web3.to_checksum_address(MOCK_SPENDER_ADDRESS),
        amount_raw
    )
    mock_tx.estimate_gas.assert_called_once_with({'from': Web3.to_checksum_address(MOCK_USER_ADDRESS)})
    expected_tx_dict = {
        'from': Web3.to_checksum_address(MOCK_USER_ADDRESS),
        'nonce': 1,
        'gas': 50000,
        'maxFeePerGas': mock_web3.eth.max_priority_fee,
        'maxPriorityFeePerGas': mock_web3.eth.max_priority_fee
    }
    mock_tx.build_transaction.assert_called_once_with(expected_tx_dict)
    mock_web3.eth.account.sign_transaction.assert_called_once_with(
        raw_tx_dict,
        MOCK_PRIVATE_KEY
    )
    mock_web3.eth.send_raw_transaction.assert_called_once_with(signed_tx_mock.raw_transaction)

def test_approve_without_private_key(token_instance_no_pk, mock_web3, mock_contract):
    """Test approving spender without a private key (relies on wallet)."""
    amount_raw = 100 * (10**18)
    mock_tx = MagicMock()
    mock_contract.functions.approve(
        Web3.to_checksum_address(MOCK_SPENDER_ADDRESS),
        amount_raw
    ).return_value = mock_tx

    # Mock estimate_gas
    mock_tx.estimate_gas.return_value = 50000

    # Mock transact
    mock_tx.transact.return_value = bytes.fromhex(MOCK_TX_HASH[2:])

    tx_hash = token_instance_no_pk.approve(MOCK_SPENDER_ADDRESS, amount_raw, MOCK_USER_ADDRESS)

    assert tx_hash == MOCK_TX_HASH

    # Verify calls
    mock_web3.eth.get_transaction_count.assert_called_once_with(Web3.to_checksum_address(MOCK_USER_ADDRESS))
    mock_contract.functions.approve.assert_called_once_with(
        Web3.to_checksum_address(MOCK_SPENDER_ADDRESS),
        amount_raw
    )
    mock_tx.estimate_gas.assert_called_once_with({'from': Web3.to_checksum_address(MOCK_USER_ADDRESS)})
    expected_tx_dict = {
        'from': Web3.to_checksum_address(MOCK_USER_ADDRESS),
        'nonce': 1,
        'gas': 50000,
        'maxFeePerGas': mock_web3.eth.max_priority_fee,
        'maxPriorityFeePerGas': mock_web3.eth.max_priority_fee
    }
    mock_tx.transact.assert_called_once_with(expected_tx_dict)
    mock_web3.eth.account.sign_transaction.assert_not_called()
    mock_web3.eth.send_raw_transaction.assert_not_called()


def test_approve_failure(token_instance, mock_web3, mock_contract):
    """Test handling of failure during approval process."""
    amount_raw = 100 * (10**18)
    mock_tx = MagicMock()
    mock_contract.functions.approve(
        Web3.to_checksum_address(MOCK_SPENDER_ADDRESS),
        amount_raw
    ).return_value = mock_tx

    # Simulate an error during estimate_gas
    mock_tx.estimate_gas.side_effect = ContractLogicError("Execution reverted")

    with pytest.raises(TokenError.ApprovalError, match="Failed to approve tokens: Execution reverted"):
        token_instance.approve(MOCK_SPENDER_ADDRESS, amount_raw, MOCK_USER_ADDRESS)

    # Verify estimate_gas was called
    mock_tx.estimate_gas.assert_called_once_with({'from': Web3.to_checksum_address(MOCK_USER_ADDRESS)})
    # Ensure subsequent steps were not called
    mock_web3.eth.get_transaction_count.assert_not_called()
    mock_tx.build_transaction.assert_not_called()
    mock_web3.eth.account.sign_transaction.assert_not_called()
    mock_web3.eth.send_raw_transaction.assert_not_called()
    mock_tx.transact.assert_not_called() 
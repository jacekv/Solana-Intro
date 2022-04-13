import yaml
import borsh

from borsh import types
from os import path
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.system_program import create_account, CreateAccountParams
from solana.sysvar import SYSVAR_RENT_PUBKEY
from solana.transaction import Transaction, TransactionInstruction, AccountMeta

from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import initialize_account, InitializeAccountParams, transfer, TransferParams
from spl.token._layouts import ACCOUNT_LAYOUT

ESCROW_ACCOUNT_SCHEMA = borsh.schema({
    'is_initialized': types.u8,
    'initializer_pubkey': types.fixed_array(types.u8, 32),
    'temp_token_account_pubkey': types.fixed_array(types.u8, 32),
    'initializer_token_to_receive_account_pubkey': types.fixed_array(types.u8, 32),
    'expected_amount': types.u64
})

ESCROW_PROGRAM_ID = PublicKey("2WkUNe6gUVRk4FZ7cw66RAUokFZi4yfszFDAa7WgjgNn")

ESCROW_ACCOUNT_SIZE = 1 + 32 + 32 + 32 + 8

LAMPORTS_PER_SOL = 1000_000_000

def getConfig():
    config_path = path.normpath(path.join(path.expanduser('~'), '.config', 'solana', 'cli', 'config.yml'))
    with open(config_path, 'r') as f:
        try:
            config = yaml.load(f, Loader=yaml.FullLoader)
        except FileNotFoundError as fnfe:
            print(fnfe)
            print('Please setup solana-cli config first')
            sys.exit(1)
    return config

def getRpcUrl():
    config = getConfig()
    if 'json_rpc_url' in config:
        return config['json_rpc_url']
    print("Failed to read RPC url from config file. Falling back to localhost")
    return "http://127.0.0.1:8899"

def establishConnection():
    """
    Establishes a connection to the Solana cluster.
    """
    global client

    rpc_url = getRpcUrl()
    try:
        client = Client(rpc_url)
    except Exception as e:
        print(e)
        print("Failed to establish connection to RPC server")
        sys.exit(1)


def setup_user_keypair() -> Keypair:
    keypair = Keypair()
    print("Requesting airdrop for Keypair")
    tx_hash = client.request_airdrop(keypair.public_key, LAMPORTS_PER_SOL * 2)
    print("Airdrop request submitted. Waiting for confirmation...")
    client.confirm_transaction(tx_hash['result'])
    print("Airdrop for Keypair confirmed")
    return keypair

def create_simple_account() -> Keypair:
    return Keypair()

def create_token_program(payer: Keypair, decimal: int) -> Token:
    token = Token.create_mint(
        conn=client,
        payer=payer,
        mint_authority=payer.public_key,
        decimals=9,
        program_id=TOKEN_PROGRAM_ID
    )
    print(f"Address of token program: {token.program_id}")
    print(f"Current supply: {token.get_mint_info().supply}")
    return token


def create_token_account(token: Token, owner: PublicKey) -> PublicKey:
    print("We are going to create an account in order to hold balance")
    owner_token_account = token.create_account(owner)
    print(f"Address of account is {owner_token_account}")
    return owner_token_account
    
def mint_token(token: Token, minter: Keypair, account: PublicKey, amount: int):
    print(f"Time to mint some tokens :) We are going to mint {amount} tokens")
    tx_hash = token.mint_to(
        dest=account,
        mint_authority=minter,
        amount=amount,
        opts=TxOpts(skip_confirmation=False)
    )
    
    print(f"Current supply: {token.get_mint_info().supply}")
    balance = token.get_balance(account)
    print(f"{minter.public_key} has {balance['result']['value']['amount']} tokens")


def init_escrow(
    fee_payer: Keypair,
    temp_account_keypair: Keypair,
    token_program: Token,
    source_token_account: PublicKey,
    receiving_token_account: PublicKey):
    print("Time to initialize the escrow")

    # create empty account using the system program
    create_temp_account_ix = create_account(
        CreateAccountParams(
            # The account that will transfer lamports to the created account
            from_pubkey=fee_payer.public_key,
            # Public key of the created account
            new_account_pubkey=temp_account_keypair.public_key,
            # Amount of lamports to transfer to the created account
            lamports=client.get_minimum_balance_for_rent_exemption(usize=ACCOUNT_LAYOUT.sizeof())["result"],
            # Amount of space in bytes to allocate to the created account
            space=ACCOUNT_LAYOUT.sizeof(),
            # Public key of the program to assign as the owner of the created account
            # Since we want to create a token account, we need to give the TOKEN_PROGRAM_ID as owner
            program_id=TOKEN_PROGRAM_ID
        )
    )

    # next instruction is to initialize the created account, which is empty
    # 
    init_temp_account_ix = initialize_account(
        InitializeAccountParams(
            # address of account to be initialized by the token program
            account=temp_account_keypair.public_key,
            # pubkey of the token program. This leads to an account, which has information for the token program
            mint=token_program.pubkey,
            # who is the owner of the token account? Owner is set in the user-space data field!
            # the account owner is the token program!
            owner=fee_payer.public_key,
            # program id of the token program
            program_id=TOKEN_PROGRAM_ID
        )
    )

    # next, we are going to transfer 100 tokens from the fee payer (alice) to the temp account
    transfer_to_temp_ix = transfer(
        TransferParams(
            amount=100,
            dest=temp_account_keypair.public_key,
            owner=fee_payer.public_key,
            program_id=TOKEN_PROGRAM_ID,
            source=source_token_account
        )
    )

    escrow_account_keypair = Keypair()

    # next, we are creating an escrow account, which is owned by the escrow program, hence ESCROW_PROGRAM_ID
    create_escrow_account_ix = create_account(
        CreateAccountParams(
            # The account that will transfer lamports to the created account
            from_pubkey=fee_payer.public_key,
            # Public key of the created account
            new_account_pubkey=escrow_account_keypair.public_key,
            # Amount of lamports to transfer to the created account
            lamports=client.get_minimum_balance_for_rent_exemption(usize=ESCROW_ACCOUNT_SIZE)["result"],
            # Amount of space in bytes to allocate to the created account
            space=ESCROW_ACCOUNT_SIZE,
            # Public key of the program to assign as the owner of the created account
            program_id=ESCROW_PROGRAM_ID
        )
    )

    # last but not least, we have to build a transcation, in order to communicate with our escrow program!
    init_escrow_ix = TransactionInstruction(
        data=bytes(1) + (10).to_bytes(8, byteorder='little'),
        keys=[
            AccountMeta(pubkey=fee_payer.public_key, is_signer=True, is_writable=False),
            AccountMeta(pubkey=temp_account_keypair.public_key, is_signer=False, is_writable=True),
            AccountMeta(pubkey=receiving_token_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=escrow_account_keypair.public_key, is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
        program_id=ESCROW_PROGRAM_ID,
    )

    # add all the instructions to the transaction
    transaction = Transaction()
    transaction.add(create_temp_account_ix)
    transaction.add(init_temp_account_ix)
    transaction.add(transfer_to_temp_ix)
    transaction.add(create_escrow_account_ix)
    transaction.add(init_escrow_ix)

    tx_hash = client.send_transaction(transaction, fee_payer, temp_account_keypair, escrow_account_keypair)
    client.confirm_transaction(tx_hash['result'])


if __name__ == "__main__":
    establishConnection()
    alice = setup_user_keypair()
    print(f"Alice's public key: {alice.public_key}")
    temp_token_account = create_simple_account()
    bob = setup_user_keypair()
    print(f"Bob's public key: {bob.public_key}")

    print()
    x_token = create_token_program(alice, decimal=9)
    alice_x_token_account = create_token_account(x_token, alice.public_key)
    mint_token(x_token, alice, alice_x_token_account, 1000)

    print()
    y_token = create_token_program(alice, decimal=9)
    alice_y_token_account = create_token_account(y_token, alice.public_key)

    init_escrow(
        alice,
        temp_token_account,
        x_token,
        alice_x_token_account,
        alice_y_token_account
    )
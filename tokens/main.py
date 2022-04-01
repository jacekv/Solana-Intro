import yaml
import json

from os import path
from solana.rpc.api import Client
from solana.rpc.core import RPCException
from solana.rpc.types import TxOpts
from solana.keypair import Keypair
from solana.publickey import PublicKey

from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID

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

def getPayer():
    """
    Tries to read the secret key from the file referenced in the config file. If no file is found, a new keypair is generated.
    """
    config = getConfig()
    if 'keypair_path' in config:
        with open(config['keypair_path'], 'rb') as f:
            # totally weird... We are reading the file as bytes, convert it to string, with utf-8 encoding,
            # load it with json, which gives us a list. Then, we are going through the list, change the numbers of 
            # byte and join all together to a byte string. Geez
            keypair = Keypair.from_secret_key(b"".join(map(lambda x: x.to_bytes(1, "big"), json.loads(f.read().decode('utf-8')))))
            return keypair
    print('Failed to create keypair from cli, falling back to new random keypair')
    keypair = Keypair()
    return Keypair()


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

if __name__ == '__main__':
    establishConnection()
    payer = getPayer()

    # print('Creating token program...')
    # token = Token.create_mint(
    #     conn=client,
    #     payer=payer,
    #     mint_authority=payer.public_key,
    #     decimals=9,
    #     program_id=TOKEN_PROGRAM_ID
    # )
    # print(f"Address of token program: {token.program_id}")
    # print(f"Current supply: {token.get_mint_info().supply}")

    # print("We are going to create an account in order to hold balance")
    # payer_token_account = token.create_account(owner=payer.public_key)
    # print(f"Address of account is {payer_token_account}")
    
    # print("Time to mint some tokens :) We are going to mint 1000 tokens")
    # tx_hash = token.mint_to(
    #     dest=payer_token_account,
    #     mint_authority=payer,
    #     amount=1000,
    #     opts=TxOpts(skip_confirmation=False)
    # )
    
    # print(f"Current supply: {token.get_mint_info().supply}")
    # balance = token.get_balance(payer_token_account)
    # print(f"{payer.public_key} has {balance['result']['value']['amount']} tokens")
    # print(f"uiAmountString {balance['result']['value']['uiAmountString']}")

    # print("Time to transfer some tokens. We are going to transfer 100 tokens")
    receiver = Keypair()
    # receiver_token_account = token.create_account(owner=receiver.public_key)
    # print(f"Address of receivers account is {receiver_token_account}")

    # print("Transfering tokens...")
    # tx_hash = token.transfer(
    #     source=payer_token_account,
    #     dest=receiver_token_account,
    #     owner=payer,
    #     amount=100,
    #     opts=TxOpts(skip_confirmation=False)
    # )

    # print(f"Current supply: {token.get_mint_info().supply}")
    # balance = token.get_balance(payer_token_account)
    # print(f"{payer.public_key} has {balance['result']['value']['amount']} tokens")
    # balance = token.get_balance(receiver_token_account)
    # print(f"{receiver.public_key} has {balance['result']['value']['amount']} tokens")


    print("AWESOME, now some time for MULTISIG token")
    party_a = Keypair()
    party_b = Keypair()
    party_c = Keypair()
    party_d = Keypair()
    party_e = Keypair()

    tx = client.request_airdrop(party_a.public_key, 2 * LAMPORTS_PER_SOL)

    print('Waiting for transaction to be finalized...')
    client.confirm_transaction(tx["result"])

    spl_token_program = Token(
        conn=client,
        program_id=TOKEN_PROGRAM_ID,
        pubkey=payer.public_key,
        payer=payer,
    )

    multisig_public_key = spl_token_program.create_multisig(
        m=3,
        multi_signers=[party_a.public_key, party_b.public_key, party_c.public_key, party_d.public_key, party_e.public_key]
    )

    print(f"Created 3/5 multisig: {multisig_public_key}")

    print('Creating token program...')
    token_multisig = Token.create_mint(
        conn=client,
        payer=payer,
        mint_authority=multisig_public_key,
        decimals=9,
        program_id=TOKEN_PROGRAM_ID
    )
    print(f"Address of token program: {token_multisig.program_id}")
    print(f"Current supply: {token_multisig.get_mint_info().supply}")

    multisig_account_pubkey = token_multisig.create_associated_token_account(owner=multisig_public_key)
    print(f"Address of account is {multisig_account_pubkey}")

    print("Time to mint some tokens :) We are going to mint 1000 tokens")
    try:
        token_multisig.mint_to(
            dest=multisig_account_pubkey,
            mint_authority=multisig_public_key,
            amount=1000,
            multi_signers=[party_a, party_b],
            opts=TxOpts(skip_confirmation=False)
        )
    except RPCException as e:
        print(e)
        print("Ops, we missed a signatute. At the end, it's 3/5 and not 2/5")
        print("Let's do it again, this time with 3 signatures ;)")
        token_multisig.mint_to(
            dest=multisig_account_pubkey,
            mint_authority=multisig_public_key,
            amount=1000,
            multi_signers=[party_a, party_b, party_e],
            opts=TxOpts(skip_confirmation=False)
        )

    print(f"Current supply: {token_multisig.get_mint_info().supply}")

    print("Time to transfer some tokens. We are going to transfer 100 tokens")
    accounts = token_multisig.get_accounts(receiver.public_key)['result']['value']
    if len(accounts) == 0:
        print(f"Receiver {receiver.public_key} has no account with this token program. We create one account")
        receiver_multisig_token_account = token_multisig.create_account(owner=receiver.public_key)
        print(f"Address of receivers account is {receiver_multisig_token_account}")

    accounts = token_multisig.get_accounts(receiver.public_key)['result']['value']
    print(f"Receiver has {len(accounts)} accounts with the token program")

    balance = token_multisig.get_balance(receiver_multisig_token_account)
    print(f"Receivers token balance is {balance['result']['value']['amount']}")

    print("Transfering tokens...")
    token_multisig.transfer(
        source=multisig_account_pubkey,
        dest=receiver_multisig_token_account,
        owner=multisig_public_key,
        amount=100,
        multi_signers=[party_a, party_b, party_e],
        opts=TxOpts(skip_confirmation=False)
    )

    balance = token_multisig.get_balance(receiver_multisig_token_account)
    print(f"Receivers token balance is {balance['result']['value']['amount']}")

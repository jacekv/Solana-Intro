import yaml
import sys
import borsh
import json
import base64

from random import random
from os import path
from borsh import types
from solana.rpc.api import Client
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import Transaction, TransactionInstruction, AccountMeta
from solana.system_program import SYS_PROGRAM_ID, create_account, create_account_with_seed, CreateAccountParams, CreateAccountWithSeedParams

client = None
payer = None
greeted_public_key = None
program_id = None

LAMPORTS_PER_SOL = 1000_000_000

GREETING_ACCOUNT_SCHEMA = borsh.schema({
    'counter': types.u32
})

GREETING_ACCOUNT = {
    'counter': 0
}

GREETING_ACCOUNT_SIZE = len(borsh.serialize(GREETING_ACCOUNT_SCHEMA, GREETING_ACCOUNT))

PROGRAM_PATH = path.normpath(path.join(path.dirname(__file__), 'dist/program'))
PROGRAM_SO_PATH = path.normpath(path.join(PROGRAM_PATH, 'helloworld.so'))
PROGRAM_KEYPAIR_PATH = path.normpath(path.join(PROGRAM_PATH, 'helloworld-keypair.json'))


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

def establishPayer():
    global payer

    fees = 0

    # each signature in a transaction on Solana costs an addition 5000 lamports per 
    feeCalculator = client.get_recent_blockhash()["result"]["value"]["feeCalculator"]

    # if I understand this function correct, it returns the number of lamports which are required in order to
    # be exempted to pay rent for storing data on-chain
    fees += client.get_minimum_balance_for_rent_exemption(GREETING_ACCOUNT_SIZE)["result"]

    # calculate the cost of sending transaction - not sure yet why
    fees += feeCalculator["lamportsPerSignature"] * 100

    payer = getPayer()

    balance = client.get_balance(payer.public_key)["result"]["value"]
    print(f"Balance for {payer.public_key} is {balance} lamports")

    if balance < fees:
        print("Not enough balance on account. Going to request an airdrop")
        tx = client.request_airdrop(payer.public_key, 2 * LAMPORTS_PER_SOL)

        print('Waiting for transaction to be finalized...')
        client.confirm_transaction(tx["result"])

        balance = client.get_balance(payer.public_key)["result"]["value"]
        print(f"Balance for {payer.public_key} is {balance} lamports")

def checkProgram():
    global greeted_public_key
    global program_id

    # loading the secret key of the Hello World program, which we deployed in order to get the program id
    with open(PROGRAM_KEYPAIR_PATH, 'rb') as f:
        keypair = Keypair.from_secret_key(b"".join(map(lambda x: x.to_bytes(1, "big"), json.loads(f.read().decode('utf-8')))))
        program_id = keypair.public_key
    
    if program_id is None:
        print(f"Failed to read program keypair at {PROGRAM_KEYPAIR_PATH}. Program may need to be deployed first")
        sys.exit(1)
    
    print(f"Program id: {program_id}")
    program_info = client.get_account_info(program_id)["result"]["value"]

    if program_info is None:
        print(f"Failed to get info for program {program_id}")
        print("Has the program been deployed?")
        sys.exit(1)

    print(f"\nProgram info: {program_info}")

    GREETING_SEED = "hello"

    # derive a public key from another key, a seed, and a program id
    if random() < 0.5:
        seed = True
        #TODO: why would we do that?
        greeted_public_key = PublicKey.create_with_seed(
            payer.public_key,
            GREETING_SEED,
            program_id
        )
    else:
        seed = False
        k = Keypair()
        greeted_public_key = k.public_key

    greeted_account = client.get_account_info(greeted_public_key)["result"]["value"]
    if greeted_account is None:
        print(f"\nCreating account {greeted_public_key} to say hello to")
        lamports = client.get_minimum_balance_for_rent_exemption(GREETING_ACCOUNT_SIZE)["result"]

        if seed:
            # this works with the PublicKey.create_with_seed function
            # it generates a new account at an address generated with from, a seed, and programId
            transaction = Transaction().add(
                create_account_with_seed(CreateAccountWithSeedParams(
                    # from_pubkey: The account who initiated this instruction
                    from_pubkey=payer.public_key,
                    # Base public key to use to derive the address of the created account.
                    # Must be the same as the base key used to create newAccountPubkey
                    base_pubkey=payer.public_key,
                    # seed: The seed to use to derive the address of the created account.
                    #seed={"length": len(GREETING_SEED), "chars": GREETING_SEED},
                    seed=GREETING_SEED,
                    # new_account_key: The pubkey of the account to be created
                    new_account_pubkey=greeted_public_key,
                    # lamports: How much funds to be transferred to pay for rent
                    lamports=lamports,
                    # space: How much space to allocate for the account
                    space=GREETING_ACCOUNT_SIZE,
                    # program_id: The account owner of this account. Token Program in this example
                    program_id=program_id
                ))
            )
            # my understanding is, that the payer is the payer for the tx and since we are using a seed to derive 
            # a public key for the account, there is no other party who signs this tx!
            tx = client.send_transaction(transaction, payer)
        else:
            transaction = Transaction().add(
                create_account(CreateAccountParams(
                    #from_pubkey: The account who initiated this instruction
                    from_pubkey=payer.public_key,
                    new_account_pubkey=greeted_public_key,
                    lamports=lamports,
                    space=GREETING_ACCOUNT_SIZE,
                    program_id=program_id
                ))
            )
            # since the payer is the payer for the tx and we are creating a new account for k,
            # both need to sign the tx!
            tx = client.send_transaction(transaction, payer, k)
        client.confirm_transaction(tx["result"])

def sayHello():
    print(f"\nGoing to say hello to {greeted_public_key}")

    instructions = TransactionInstruction(
        keys=[AccountMeta(greeted_public_key, False, True)],
        program_id=program_id,
        data=bytes(0)    
    )

    tx = client.send_transaction(
        Transaction().add(instructions),
        payer
    )
    client.confirm_transaction(tx["result"])

def reportGreetings():
    account_info = client.get_account_info(greeted_public_key)["result"]["value"]
    if account_info is None:
        print("Can't find the greeted account")
        sys.exit(1)

    greeting = borsh.deserialize(
        GREETING_ACCOUNT_SCHEMA,
        base64.b64decode(account_info["data"][0])
    )
    print(f"{greeted_public_key} has been greeted {greeting['counter']} time(s)")

if __name__ == "__main__":
    print("Let's say hello to a Solana account...")

    # setup the connection to the cluster
    establishConnection()
    print(f"Connection established: {client.is_connected()}")

    # determine who is going to pay the fees
    establishPayer()

    # check if the hello world BPF program has been deployed
    checkProgram()

    # call the program on-chain
    sayHello()

    # get the data from the chain to see what's the status
    reportGreetings()
# Function calls in program

## Commands
Start Solana test validator: `solana-test-validator`
Start the logging: `solana logs`

To compile the code: `cargo build-bpf`
To deploy: `solana program deploy target/deploy/function_calls.so`

Create a virtual environment: `python3 -m virtualenv --python /path/to/python3 venv`
Activate the virtual environment: `source venv/bin/activate`
Install requirements: `pip install -r requirements.txt`
Fire up the script: `python main.py`

## Learning
In this part I am learning on how to call different functions within a program.

We are having a simple calculator, which is able to perform to actions, add and sub.

The python script provides the following data:
 0x0 for add, two 8 bytes values, which are going to be added together. The result is stored in an account
 0x1 for sub, two 8 bytes values, which are going to be subtracted from each other. The result is stored in an account

We don't have an ABI as in EVM based contracts, where functions are stored in a JSON. Instead we have a binary
and we need to know how to call the different functions. I am using a byte to differentiate between add and sub.
We could also use 2 or more bytes to do that :)

I also learned that Solana programs are stateless, in camparison to EVM based contracts, which are stateful.
We have to provide an account, where the data can be stored in.

So the question arises: Is there some sort of call functionality in Solana, where we execute the program,
receive a result and do not affect the state or send a tx?

The answer is currently the simulate_transaction rpc call. I included it into the code too. But I haven't
seen the possibility to get the result during the simulation.
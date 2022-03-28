Code is commented. Feel free to have a look :)

The Cargo.toml file contains the following two lines:
```
[features]
no-entrypoint = []
```

and 

```
[lib]
name = "helloworld"
crate-type = ["cdylib", "lib"]
```

In case of the features part, here is the official documentation: 

```
Solana Rust programs may depend directly on each other in order to gain access to instruction helpers when making cross-program invocations. When doing so it's important to not pull in the dependent program's entrypoint symbols because they may conflict with the program's own. To avoid this, programs should define an no-entrypoint feature in Cargo.toml and use to exclude the entrypoint.
```

Let's get started :)

First, make sure Solana CLI is installed:
```bash
solana --version
```
In Solana, a set of validators make up a cluster. We've three clusters: mainnet, devnet, and localhost.
For our purpose, we'll use the local cluster. Let's set the CLI config to the localhost cluster using the config set command:
```bash
solana config set --url localhost
```

Next, we are going to create a new keypair:
```bash
solana-keygen new
```

Note: Never publish the seed phrase anywhere!! Anyone who gets the seed phrase will be able to steal your funds.

Start local cluster:
```bash
solana-test-validator
```
In another terminal we are going to log:
```bash
solana logs
```

To build the program, we use the following command:
```bash
cargo build-bpf --manifest-path=Cargo.toml --bpf-out-dir=dist/program
```

To deploy the program we need to run:
```bash
solana program deploy dist/program/helloworld.so
```
The output should be something like this:
```bash
Program Id: ALj1dEALpncL3wFnTGhieSWFVkvgV5FDSCgmmVNSPFCc
```

If you check the terminal with the logs, you will see some output.

We did it :) We deploy a Solana program to the chain!
Time to interact with it from the client side.

To interact with a Solana node inside a Python application, we use the 
 https://github.com/michaelhly/solana-py library.

We are going to create a virtual environment and activate it:
```bash
python3 -m virtualenv --python /Path/To/Python3 venv
source venv/bin/activate
pip install solana
```

There is some code in the main.py file. In order to execute it, feel free to fire it up with
```bash
python main.py
```
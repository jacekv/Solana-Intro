Accounts have an owner field. The docs (https://docs.solana.com/developing/programming-model/accounts#ownership-and-assignment-to-programs) are saying the following about the owner field:

```
The owner is a program id. The runtime grants the program write access to the account if its id matches the owner. For the case of the System program, the runtime allows clients to transfer lamports and importantly assign account ownership, meaning changing the owner to a different program id. If an account is not owned by a program, the program is only permitted to read its data and credit the account.
```

Is it possible to change the owner of an account?
Yes, it is. A program is able to change the owner of an account with the following code:
```rust
let config_account = &accounts[0]; //config_account is AccountInfo
msg!("Account owner: {}", config_account.owner);
let new_owner_key = Pubkey::new(instruction_data.get(1..33).ok_or(ProgramError::InvalidArgument)?);
config_account.assign(&new_owner_key);
msg!("Account owner: {}", config_account.owner);
```
Taken from: https://github.com/solana-labs/solana/blob/85a2e599bbbf3d51f201167f921718e52c7ce59f/programs/bpf/rust/realloc/src/processor.rs#L54

Following attack scenario:
An attacker creats an account and a Solana program. The Solana program writes data into the account and changes the owner of the account to the program to be attacked.

This does not work, since on order to change the owner, the data field of an account has to be either empty or zero initalized.

```
// Only the owner of the account may change owner and
//   only if the account is writable and
//   only if the account is not executable and
//   only if the data is zero-initialized or empty
```
taken from: https://github.com/solana-labs/solana/blob/bf5725229843521e0c50fcc2e81d2c853d2d60eb/program-runtime/src/pre_account.rs
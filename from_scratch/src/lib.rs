
// We are importing the borsh.
// BorshSerialize is used for converting data into bytecode while
// BorshDeserialize is used for converting bytecode into data.
// Serializing is necessary because the programs must be parsed in BPF format.
use borsh::{BorshDeserialize, BorshSerialize};

// The next use declaration brings the solana_program crate into the scope.
// This crate contains a bunch of Solana source code that we'll
// leverage to write on-chain programs.
use solana_program::{
    // account_info contains next_account_info, which is a public function
    // that returns the next AccountInfo or a NotEnoughAccountKeys error.
    // AccountInfo is a public struct that contains the accounts's 
    // information - like the PubKey and owner.
    account_info::{next_account_info, AccountInfo},
    // In entrypoint, we have an entrypoint! makro that we will use to
    // call our program. 
    entrypoint,
    // ProgramResult is a Result type with Ok or ProgramError if the program fails.
    entrypoint::ProgramResult,
    // msg is used for logging in Solana. Solana considers println! 
    // as computationally expensive
    msg,
    // ProgramError allows you to implement program-specific error types and see
    // them returned by the Solana runtime.
    program_error::ProgramError,
    // PubKey is struct.
    pubkey::Pubkey,
};
// we also have to add those dependencies to the Cargo.toml file.
// Have a look into the Cargo.toml file. There you will find 3 dependencies.

// #[derive] belongs to another group of macros known as procedural macros.
// Deriving tells the compiler to provide some basic implementations for some traits.
// Besides the serialize and deserializing traits, we also derive the Debug trait.
// In Rust, traits allow us to share behaviour across non-abstract types like structs
// and facilitates code reuse. They are like interfaces in other languages.
// Debug trait makes types like structs and enums printable.
// Next, we declare the GreetingAccount struct using the pub keyword which makes it
// publicly accessible so other programs can use it. By default, everything in Rust is
// private, with two exceptions: Associated items in a pub Trait and Enum variants in a
// pub enum. A struct or structure is a custom data type that allows us to package
// related values. Each field defined within a struct has a name and a type.
// GreetingAccount has only one field: counter with a type of u32, an
// unsigned(positive) 32-bit integer.
#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct GreetingAccount {
    // number of greetings
    pub counter: u32,
}

// All Solana programs must have an entrypoint that the runtime looks up and
// calls when invoking a program. The entrypoint! macro declares process_instruction
// as the entry to our program
entrypoint!(process_instruction);

// We implement process_instruction via a function with visibility set to public.
// Each parameter has an ampersand operator. This is because Solana programs do not store 
// data, data is stored in accounts. The ampersand tells Rust that we do not own this
// data, we are just borrow it, which is called referencing.
pub fn process_instruction(
    // program_id is the public key of the currently executing program accounts.
    // When you want to call a program, you must pass this id, so that Solana knows
    // which program is to be executed
    program_id: &Pubkey,
    // accounts if a reference to an array of accounts to say hello to. It is the list
    // of accounts that will be operated upon in this code
    accounts: &[AccountInfo],
    // _instruction_data - any additional data passed as u8 array. In this program
    // we won't be consuming this data because it's just hello. We add the underscore
    // to tell the compiler to chill.
    _instruction_data: &[u8],
// The function returns ProgramResult which we imported earlier.
// ProgramResult is of Result type which is an Enum with two variants:
// Ok representing success and containing a value, and Err representing error and
// containing an error value. ProgramResult will give as an Ok() as a success if our
// instruction is processed or a ProgramError if it fails.
) -> ProgramResult {
    // print message on the program log
    msg!("Hello World Rust program entrypoint");

    // We create a new variable accounts_iter using the let keyword.
    // We iterate over each account using the iter() method and bind them to the
    // variable as mutable references.
    // Rust references are immutable by default so we have to specify that we want to
    // be able to write to each account by adding the mut keyword.
    let accounts_iter = &mut accounts.iter();

    // As I mentioned, next_account_info will return the account we want to say hello
    // to or an error if it doesn't find an account.
    // It's able to do this because the function returns the Result type we talked of earlier.
    // The question mark operator ? hides some of the boilerplate of propagating errors.
    let account = next_account_info(accounts_iter)?;

    // Only the program that owns the account should be able to modify its data.
    // This check ensures that if the account.owner public key does not equal
    // the program_id we will return an IncorrectProgramId error.
    if account.owner != program_id {
        msg!("Greeted account does not have the correct program id");
        return Err(ProgramError::IncorrectProgramId);
    }

    // try_from_slice is a method from the borsh crate that we use to deserialize an instance 
    // from slice of bytes to actual data our program can work with. Under the hood it looks like
    // this: fn try_from_slice(v: &[u8]) -> Result<Self>
    // try_from_slice could also return an error if the deserialization fails - note the
    // ? operator because it implements the Result type. We use the actual account data 
    // we borrowed to get the counter value and increment it by one and send it back to the runtime
    // in serialized format.
    let mut greeting_account = GreetingAccount::try_from_slice(&account.data.borrow())?;
    greeting_account.counter += 1;
    greeting_account.serialize(&mut &mut account.data.borrow_mut()[..])?;

    // We log how many time the count has been incremented by using the msg! macro
    msg!("Greeted {} time(s)!", greeting_account.counter);

    Ok(())
}

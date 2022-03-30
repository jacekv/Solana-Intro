use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    msg,
    pubkey::Pubkey,
    program_error::ProgramError,
};

use borsh::{BorshDeserialize, BorshSerialize};

use crate::instruction::Instruction;

#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct CalculatorResult {
    // result of the calculation is stored here
    pub result: u64,
    pub a: u64,
    pub b: u64,
}


pub struct Processor;
impl Processor {
    pub fn process(program_id: &Pubkey, accounts: &[AccountInfo], instruction_data: &[u8]) -> ProgramResult {
        let accounts_iter = &mut accounts.iter();
        let account = next_account_info(accounts_iter)?;
        if account.owner != program_id {
            msg!("Greeted account does not have the correct program id");
            return Err(ProgramError::IncorrectProgramId);
        }

        let mut calculation_result_account = CalculatorResult::try_from_slice(&account.data.borrow())?;

        let instruction = Instruction::unpack(instruction_data)?;

        match instruction {
            Instruction::Add { a, b } => {
                msg!("Instruction: Add {} {}", a, b);
                Self::add(&mut calculation_result_account, a, b);
            }
            Instruction::Sub { a, b} => {
                msg!("Instruction: Sub {} {}", a, b);
                Self::sub(&mut calculation_result_account, a, b);
            }
        }
        calculation_result_account.serialize(&mut &mut account.data.borrow_mut()[..])?;
        Result::Ok(())
    }

    fn add(account: &mut CalculatorResult, a: u64, b: u64) {
        account.result = a + b;
        account.a = a;
        account.b = b;
    }

    fn sub(account: &mut CalculatorResult, a: u64, b: u64) {
        account.result = a - b;
        account.a = a;
        account.b = b;
    }
}
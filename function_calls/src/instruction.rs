// instruction.rs is responsible for decoding instruction_data so
use std::convert::TryInto;
use solana_program::program_error::ProgramError;

use crate::error::InstructionError::InvalidInstruction;

pub enum Instruction {
    // we have two instructions, add -> addition,
    // and sub -> subtraction
    Add {
        a: u64,
        b: u64,
    },
    Sub {
        a: u64,
        b: u64,
    },
}

impl Instruction {
    pub fn unpack(input: &[u8]) -> Result<Self, ProgramError> {
        let (tag, rest) = input.split_first().ok_or(InvalidInstruction)?;
        let (a, b) = rest.split_at(8); 

        Ok(match tag {
            0 => Self::Add {
                a: Self::unpack_amount(a)?,
                b: Self::unpack_amount(b)?,
            },
            1 => Self::Sub {
                a: Self::unpack_amount(a)?,
                b: Self::unpack_amount(b)?,
            },
            _ => return Err(InvalidInstruction.into()),
        })
    }

    fn unpack_amount(input: &[u8]) -> Result<u64, ProgramError> {
        let amount = input
            .get(..8)
            .and_then(|slice| slice.try_into().ok())
            .map(u64::from_le_bytes)
            .ok_or(InvalidInstruction)?;
        Ok(amount)
    }
}
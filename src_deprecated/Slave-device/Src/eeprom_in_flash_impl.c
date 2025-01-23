/*
 * eeprom_in_flash_impl.c
 *
 *  Created on: 13 июл. 2021 г.
 *      Author: sa100 (sergio.rudenko@gmail.com)
 */

#include "eeprom_in_flash.h"
#include "HAL_flash.h"

// ----- EEPROM_IN_FLASH Implementation ---------------------------------------
void eeprom_in_flash_page_erase(uint32_t address)
{
    FLASH_Unlock();
    FLASH_ErasePage(address);
    FLASH_Lock();
}

void eeprom_in_flash_write_word(uint32_t address, uint32_t u32)
{
	FLASH_Unlock();
	FLASH_ProgramWord(address, u32);
	FLASH_Lock();
}

void eeprom_in_flash_write_half_word(uint32_t address, uint16_t u16)
{
	FLASH_Unlock();
	FLASH_ProgramHalfWord(address, u16);
	FLASH_Lock();
}


//void
//eeprom_in_flash_page_erase(uint32_t address)
//{
//  uint32_t PageError = 0;
//
//  /* Fill EraseInit structure*/
//  FLASH_EraseInitTypeDef EraseInitStruct =
//    {
//      .TypeErase = FLASH_TYPEERASE_PAGES,
//      .PageAddress = address,
//      .NbPages = 1
//    };
//
//  HAL_FLASH_Unlock();
//  HAL_FLASHEx_Erase(&EraseInitStruct,
//                    &PageError);
//  HAL_FLASH_Lock();
//}
//
//void
//eeprom_in_flash_write(uint32_t address, uint32_t chunk)
//{
//  if (address % sizeof(uint32_t) == 0)
//  {
//    HAL_FLASH_Unlock();
//    HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD,
//                      address, chunk);
//    HAL_FLASH_Lock();
//  }
//}

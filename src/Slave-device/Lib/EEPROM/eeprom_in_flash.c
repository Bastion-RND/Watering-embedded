/*
 * eeprom_in_flash.c
 *
 *  Created on: Jul 12, 2021
 *      Author: sa100 (sergio.rudenko@gmail.com)
 */

#include "eeprom_in_flash.h"

/* ------------------------------------------------------------------------ */
#define EEPROM_IN_FLASH_PAGE_0_ADDR			((uint32_t)EEPROM_IN_FLASH_BASE_ADDRESS)
#define EEPROM_IN_FLASH_PAGE_1_ADDR			((uint32_t)EEPROM_IN_FLASH_BASE_ADDRESS + EEPROM_IN_FLASH_PAGE_SIZE)

#define EEPROM_IN_FLASH_ERASED_PAGE_MARKER	((uint32_t)(EEPROM_IN_FLASH_ERASED_DATA & 0xFFFFFFFF))
#define EEPROM_IN_FLASH_ACTIVE_PAGE_MARKER	((uint32_t)(~EEPROM_IN_FLASH_ERASED_DATA & 0xFFFFFFFF))
#define EEPROM_IN_FLASH_RECEIVE_DATA_MARKER	((uint32_t)(EEPROM_IN_FLASH_ERASED_DATA ? 0x0000FFFF: 0xFFFF0000))

#define EEPROM_IN_FLASH_RECORD_SIZE			(sizeof(uint32_t))
#define EEPROM_IN_FLASH_RECORD_COUNT		(EEPROM_IN_FLASH_PAGE_SIZE / EEPROM_IN_FLASH_RECORD_SIZE - 1)


/* ------------------------------------------------------------------------ */
/* private variables */
static uint32_t	lastRecordOffset;

/**
 *
 */
static EIF_PageStatus_t
get_page_status(uint32_t pageAddress)
{
  EIF_PageStatus_t Status;
  uint32_t pageStatus = *(volatile uint32_t*)pageAddress;

  switch (pageStatus)
  {
    case EEPROM_IN_FLASH_ERASED_PAGE_MARKER:
      Status = ERASED_PAGE;
      break;

    case EEPROM_IN_FLASH_ACTIVE_PAGE_MARKER:
      Status = ACTIVE_PAGE;
      break;

    case EEPROM_IN_FLASH_RECEIVE_DATA_MARKER:
      Status = RECEIVE_DATA;
      break;

    default:
      Status = INVALID_STATUS;
  }
  return Status;
}

/**
 *
 */
static void
set_page_status(uint32_t pageAddress, EIF_PageStatus_t Status)
{
  switch (Status)
  {
    case ACTIVE_PAGE:
      eeprom_in_flash_write_half_word(pageAddress + 0x02,
                                      EEPROM_IN_FLASH_ACTIVE_PAGE_MARKER >> 16);
      eeprom_in_flash_write_half_word(pageAddress,
                                      EEPROM_IN_FLASH_ACTIVE_PAGE_MARKER & 0xFFFF);
      break;

    case RECEIVE_DATA:
      eeprom_in_flash_write_word(pageAddress,
                                 EEPROM_IN_FLASH_RECEIVE_DATA_MARKER);
      break;

    default:
      break;
  }
}


/**
 * @brief Returns last record offset
 * @param pageAddress	:flash page base address
 * @return offset 		:[0..(FLASH_PAGE_SIZE - RECORD_SIZE)]
 */
static uint32_t
get_last_record_offset(uint32_t pageAddress)
{
  EIF_Record_t* pRecord = (EIF_Record_t*)(pageAddress);

  for (int i = EEPROM_IN_FLASH_RECORD_COUNT; i > 0; i--)
  {
    if (pRecord[i].u32 != EEPROM_IN_FLASH_ERASED_DATA)
    {
      return (EEPROM_IN_FLASH_RECORD_SIZE * i);
    }
  }
  return 0;
}


/**
 *
 */
static uint32_t
get_flash_address(uint32_t pageAddress, uint16_t eepromAddress)
{
  EIF_Record_t* pRecord = (EIF_Record_t*)(pageAddress);

  if (lastRecordOffset == 0)
  {
    lastRecordOffset = get_last_record_offset(pageAddress);
  }

  for (int i = lastRecordOffset / EEPROM_IN_FLASH_RECORD_SIZE; i > 0; i--)
  {
    if (pRecord[i].address == eepromAddress)
    {
      return (pageAddress + EEPROM_IN_FLASH_RECORD_SIZE * i);
    }
  }
  return 0;
}


/**
 *
 */
static uint32_t
get_active_page_address()
{
  uint32_t result;

  if (get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) == ACTIVE_PAGE &&
      get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR) != INVALID_STATUS)
  {
    result = EEPROM_IN_FLASH_PAGE_0_ADDR;
  }
  else if (get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR) == ACTIVE_PAGE &&
           get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) != INVALID_STATUS)
  {
    result = EEPROM_IN_FLASH_PAGE_1_ADDR;
  }
  else
  {
    return 0; /* ERROR */
  }
  return result;
}

/**
 *
 */
static bool
is_page_full()
{
  uint32_t pageAddress = get_active_page_address();

  if (pageAddress)
  {
    if (lastRecordOffset == 0)
    {
      lastRecordOffset = get_last_record_offset(pageAddress);
    }
    return (lastRecordOffset >= (EEPROM_IN_FLASH_PAGE_SIZE - EEPROM_IN_FLASH_RECORD_SIZE));
  }
  return false; /* ERROR, assume page is full */
}


/**
 *
 */
static void
transfer_data()
{
  uint32_t sourcePageAddress;
  uint32_t destinationPageAddress;

  EIF_Record_t* pRecord;

  /* Set Source and Destination */
  if (get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) == ACTIVE_PAGE &&
      get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR) == RECEIVE_DATA)
  {
    sourcePageAddress = EEPROM_IN_FLASH_PAGE_0_ADDR;
    destinationPageAddress = EEPROM_IN_FLASH_PAGE_1_ADDR;
  }
  else if (get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR) == ACTIVE_PAGE &&
           get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) == RECEIVE_DATA)
  {
    sourcePageAddress = EEPROM_IN_FLASH_PAGE_1_ADDR;
    destinationPageAddress = EEPROM_IN_FLASH_PAGE_0_ADDR;
  }
  else
  {
    return; /* Not in transfer data procedure... */
  }

  lastRecordOffset = get_last_record_offset(destinationPageAddress);
  pRecord = (EIF_Record_t*)(sourcePageAddress);

  /* Transfer data couples */
  for (int i = EEPROM_IN_FLASH_RECORD_COUNT; i > 0; i--)
  {
    if (pRecord[i].u32 != EEPROM_IN_FLASH_ERASED_DATA &&
        get_flash_address(destinationPageAddress, pRecord[i].address) == 0)
    {
      lastRecordOffset += EEPROM_IN_FLASH_RECORD_SIZE;
      eeprom_in_flash_write_word(destinationPageAddress + lastRecordOffset, pRecord[i].u32);
    }
  }

  /* Switch to Active page and format Second page */
  eeprom_in_flash_page_erase(sourcePageAddress);
  set_page_status(destinationPageAddress, ACTIVE_PAGE);
}


/**
 *
 */
static size_t
read(uint16_t eepromAddress, uint8_t *data, size_t size)
{
  uint32_t flashAddress;
  EIF_Record_t Record;
  size_t result = 0;

  uint32_t pageAddress = get_active_page_address();

  while (pageAddress && size && eepromAddress < 0xFFFF)
  {
    flashAddress = get_flash_address(pageAddress, eepromAddress & ~(0x1));

    if (flashAddress) {
      Record.u32 = *(uint32_t*)flashAddress;
    }
    else {
      Record.u32 = 0;
    }

    if ((eepromAddress % 2) || size == 1)
    {
      if (eepromAddress % 2) {
        *data = Record.data.u8[1];
      }
      else {
        *data = Record.data.u8[0];
      }
      eepromAddress += 1;
      result += 1;
      data += 1;
      size -= 1;
    }
    else
    {
      data[0] = Record.data.u8[0];
      data[1] = Record.data.u8[1];
      eepromAddress += 2;
      result += 2;
      data += 2;
      size -= 2;
    }
  }
  return result;
}


/**
 *
 */
static size_t
write(uint16_t eepromAddress, uint8_t *data, size_t size)
{
  uint32_t flashAddress;
  EIF_Record_t Record;
  size_t result = 0;

  uint32_t pageAddress = get_active_page_address();
  uint16_t u16;

  while (pageAddress && size && eepromAddress < 0xFFFF)
  {
    /* Check last record offset and Page Full */
    if (!lastRecordOffset)
    {
      lastRecordOffset = get_last_record_offset(pageAddress);
    }
    if (is_page_full())
    {
      pageAddress = (pageAddress != EEPROM_IN_FLASH_PAGE_0_ADDR) ?
                    EEPROM_IN_FLASH_PAGE_0_ADDR : EEPROM_IN_FLASH_PAGE_1_ADDR;

      set_page_status(pageAddress, RECEIVE_DATA);
      transfer_data();

      pageAddress = get_active_page_address();

      if (!pageAddress)
      {
        return 0; /* ERROR */
      }
    }

    flashAddress = get_flash_address(pageAddress, eepromAddress & ~(0x1));

    if (flashAddress) {
      Record.u32 = *(uint32_t*)flashAddress;
      u16 = Record.data.u16;
    }
    else {
      Record.address = eepromAddress & ~(0x1);
      Record.data.u16 =  0;
      u16 = 0;
    }

    if ((eepromAddress % 2) || size == 1)
    {
      if (eepromAddress % 2 == 0)
      {
        Record.data.u8[0] = *data;
      }
      else
      {
        Record.data.u8[1] = *data;
      }
      eepromAddress += 1;
      result += 1;
      data += 1;
      size -= 1;
    }
    else
    {
      Record.data.u8[0] = data[0];
      Record.data.u8[1] = data[1];
      eepromAddress += 2;
      result += 2;
      data += 2;
      size -= 2;
    }

    if (Record.data.u16 != u16)
    {
      /* Write data */
      lastRecordOffset += EEPROM_IN_FLASH_RECORD_SIZE;
      eeprom_in_flash_write_word(pageAddress + lastRecordOffset, Record.u32);
    }
  }
  return result;
}

/**
 *
 */
static void
format()
{
  if (get_last_record_offset(EEPROM_IN_FLASH_PAGE_0_ADDR) ||
      get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) != ERASED_PAGE)
  {
    eeprom_in_flash_page_erase(EEPROM_IN_FLASH_PAGE_0_ADDR);
  }
  if (get_last_record_offset(EEPROM_IN_FLASH_PAGE_1_ADDR) ||
      get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR) != ERASED_PAGE)
  {
    eeprom_in_flash_page_erase(EEPROM_IN_FLASH_PAGE_1_ADDR);
  }
  set_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR, ACTIVE_PAGE);
  lastRecordOffset = 0;
}


/**
 *
 */
static void
init()
{
  if (get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) == INVALID_STATUS)
  {
    eeprom_in_flash_page_erase(EEPROM_IN_FLASH_PAGE_0_ADDR);
  }

  if (get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR) == INVALID_STATUS)
  {
    eeprom_in_flash_page_erase(EEPROM_IN_FLASH_PAGE_1_ADDR);
  }

  /* Both page have same status: ERROR */
  if (get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) ==
      get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR))
  {
    EepromInFlash.format();
  }

  /* Finalize interrupted transfer */
  if (get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) == ERASED_PAGE &&
      get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR) == RECEIVE_DATA)
  {
    set_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR, ACTIVE_PAGE);
  }
  if (get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR) == ERASED_PAGE &&
      get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) == RECEIVE_DATA)
  {
    set_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR, ACTIVE_PAGE);
  }

  /* Complete data transfer procedure if necessary */
  if (get_page_status(EEPROM_IN_FLASH_PAGE_0_ADDR) == RECEIVE_DATA ||
      get_page_status(EEPROM_IN_FLASH_PAGE_1_ADDR) == RECEIVE_DATA)
  {
    transfer_data();
  }

  lastRecordOffset = 0;
}


/* weak functions */
__attribute__((weak)) void
eeprom_in_flash_page_erase(uint32_t address)
{
  (void) address;
}

__attribute__((weak)) void
eeprom_in_flash_write_word(uint32_t address, uint32_t u32)
{
  (void) address;
  (void) u32;
}

__attribute__((weak)) void
eeprom_in_flash_write_half_word(uint32_t address, uint16_t u16)
{
  (void) address;
  (void) u16;
}

/* instance */
const EepromInFlash_t EepromInFlash =
  {
    .init 		= init,
    .format		= format,

    .read		= read,
    .write		= write,
  };

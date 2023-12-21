/*
 * eeprom_in_flash.h
 *
 *  Created on: Jul 12, 2021
 *      Author: sa100 (sergio.rudenko@gmail.com)
 */

#ifndef EEPROM_IN_FLASH_H_
#define EEPROM_IN_FLASH_H_

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#include "eeprom_in_flash_conf.h"

/* ------------------------------------------------------------------------ */

/* ------------------------------------------------------------------------ */

typedef enum EIF_PageStatus_
{
  INVALID_STATUS,
  RECEIVE_DATA,
  ACTIVE_PAGE,
  ERASED_PAGE,
}
EIF_PageStatus_t;


typedef union EIF_Record_ {
  struct {
    union {
      uint8_t 	u8[2];
      uint16_t 	u16;
    } 			data;
    uint16_t 	address;
  };
  uint32_t 		u32;
}
EIF_Record_t;


typedef struct EepromInFlash_
{
  void 	(*init)(void);
  void 	(*format)(void);

  //	bool	(*is_full)(void);
  //	bool	(*is_empty)(void);
  //	size_t	(*get_size)(void);

  size_t	(*write)(uint16_t eepromAddress, uint8_t *data, size_t size);
  size_t	(*read)(uint16_t eepromAddress, uint8_t *data, size_t size);

} EepromInFlash_t;


/* ------------------------------------------------------------------------ */
/* instance */
extern const EepromInFlash_t EepromInFlash;


/* ------------------------------------------------------------------------ */
/* implementation functions prototypes */
void eeprom_in_flash_page_erase(uint32_t address);
void eeprom_in_flash_write_word(uint32_t address, uint32_t u32);
void eeprom_in_flash_write_half_word(uint32_t address, uint16_t u16);


#endif /* EEPROM_IN_FLASH_H_ */

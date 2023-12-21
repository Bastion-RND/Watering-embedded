/*
 * eeprom_in_flash_conf.h
 *
 *  Created on: Jul 12, 2021
 *      Author: sa100 (sergio.rudenko@gmail.com)
 */

#ifndef EEPROM_IN_FLASH_CONF_H_
#define EEPROM_IN_FLASH_CONF_H_

#include "HAL_device.h"

/* MM32f031K6 */
#define FLASH_SIZE (32 * 1024)
#define FLASH_PAGE_SIZE (1024)

#define EEPROM_IN_FLASH_PAGE_SIZE		(FLASH_PAGE_SIZE)
#define EEPROM_IN_FLASH_BASE_OFFSET		(FLASH_SIZE - FLASH_PAGE_SIZE * 2)
#define EEPROM_IN_FLASH_BASE_ADDRESS	(FLASH_BASE + EEPROM_IN_FLASH_BASE_OFFSET)

#define EEPROM_IN_FLASH_ERASED_DATA		(0xFFFFFFFF)

#endif /* EEPROM_IN_FLASH_CONF_H_ */

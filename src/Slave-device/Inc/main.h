/*
 * main.h
 */

#ifndef MAIN_H_
#define MAIN_H_

#include <stdint.h>
#include <stddef.h>

#include "HAL_device.h"
#include "configuration.h"


#define FREQUENCY_HZ 	1000UL
#define MCU_UID_ADDRESS 0x1FFFF7E8


/* types */

#pragma pack(push, 1)

typedef struct DeviceConfig_ {
	union {
		struct{
			uint32_t boot_count;
//			uint16_t soil_humidity_MAX;
			uint8_t soil_humidity_LAST;
		};
		uint8_t u8[5];
	};
} DeviceConfig_t;

#pragma pack(pop)

#pragma pack(push, 1)

typedef struct LoraPackage_ {
	union {
		struct{
			uint8_t MCU_ID[4]; //0xcc4460b1
			uint8_t soil_humidity;
			uint8_t battery_percent;
		};
		uint8_t u8[6];
	};
} LoraPackage_t;

#pragma pack(pop)

typedef enum{
	OTHER_RESET = 0,
	HARD_RESET = 1,
	SOFT_RESET = 2
} BootStatus;

#endif /* MAIN_H_ */

/*
 * lora_impl.h
 *
 *  Created on: Dec 6, 2023
 *      Author: Odrinari
 */

#ifndef LORA_IMPL_H_
#define LORA_IMPL_H_

#include "driver_llcc68.h"
#include "HAL_conf.h"
#include "gpio.h"
#include "configuration.h"

volatile unsigned char spi0_rx_flag;
volatile unsigned char spi0_tx_flag;

uint8_t spi_init(void);
uint8_t spi_deinit(void);
uint8_t spi_write_read(uint8_t *in_buf, uint32_t in_len,
                                        uint8_t *out_buf, uint32_t out_len);
uint8_t reset_gpio_init(void);
uint8_t reset_gpio_deinit(void);
uint8_t reset_gpio_write(uint8_t data);
uint8_t busy_gpio_init(void);
uint8_t busy_gpio_deinit(void);
uint8_t busy_gpio_read(uint8_t *value);

void txen_init();
uint8_t txen_write(uint8_t data);

void debug_print(const char *const fmt, ...);
void receive_callback(uint16_t type, uint8_t *buf, uint16_t len);
unsigned int SPI_Read_Write_Byte(SPI_TypeDef* SPIx, unsigned char tx_data);
void SPI_handler(void);
void dio1_interrupt_init();

#endif /* LORA_IMPL_H_ */

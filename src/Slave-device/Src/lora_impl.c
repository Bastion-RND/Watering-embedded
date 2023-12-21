/*
 * lora_impl.c
 *
 *  Created on: Dec 6, 2023
 *      Author: Odrinari
 */

#include "lora_impl.h"

void txen_init()
{
	gpio_pin_configure(LORA_TXEN_PORT, LORA_TXEN_PIN, GPIO_Mode_Out_PP);
}

uint8_t txen_write(uint8_t data)
{
    if (data != 0)
    {
        /* set high */
    	GPIO_WriteBit(LORA_TXEN_PORT, LORA_TXEN_PIN, SET);
    }
    else
    {
        /* set low */
    	GPIO_WriteBit(LORA_TXEN_PORT, LORA_TXEN_PIN, RESET);
    }
    return 0;
}


void dio1_interrupt_init()
{
	GPIO_InitTypeDef GPIO_InitStructure;
	NVIC_InitTypeDef NVIC_InitStructure;
	EXTI_InitTypeDef EXTI_InitStructure;

	RCC_APB2PeriphClockCmd(RCC_APB2Periph_SYSCFG, ENABLE);
	RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOA, ENABLE);

    GPIO_InitStructure.GPIO_Pin  = LORA_DIO1_PIN;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPD;
    GPIO_Init(LORA_DIO1_PORT, &GPIO_InitStructure);

    NVIC_InitStructure.NVIC_IRQChannel = EXTI2_3_IRQn;
    NVIC_InitStructure.NVIC_IRQChannelPriority = 2;
    NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
    NVIC_Init(&NVIC_InitStructure);

    SYSCFG_EXTILineConfig(EXTI_PortSourceGPIOA, EXTI_PinSource2);
    EXTI_InitStructure.EXTI_Line = EXTI_Line2;
    EXTI_InitStructure.EXTI_Mode = EXTI_Mode_Interrupt;
    EXTI_InitStructure.EXTI_Trigger = EXTI_Trigger_Rising;
    EXTI_InitStructure.EXTI_LineCmd = ENABLE;
    EXTI_Init(&EXTI_InitStructure);


}

uint8_t spi_init(void)
{
    SPI_InitTypeDef SPI_InitStructure;
    GPIO_InitTypeDef GPIO_InitStructure;
    NVIC_InitTypeDef NVIC_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_SPI1, ENABLE);                        //SPI2 clk enable
    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOA, ENABLE);
    //RCC_AHBPeriphClockCmd(RCC_AHBPeriph_GPIOB, ENABLE);

    //GPIO_PinAFConfig(GPIOA, GPIO_PinSource4, GPIO_AF_0);                       //SPI_NSS   PA4
    GPIO_PinAFConfig(GPIOA, GPIO_PinSource5, GPIO_AF_0);                       //SPI_SCK   PA5
    GPIO_PinAFConfig(GPIOA, GPIO_PinSource6, GPIO_AF_0);                       //SPI_MISO  PA6
    GPIO_PinAFConfig(GPIOA, GPIO_PinSource7, GPIO_AF_0);                       //SPI_MOSI  PA7

    GPIO_InitStructure.GPIO_Pin  = SPI1_NSS_Pin;                                  //SPI_NSS
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;                             //Push to avoid multiplexing output
    GPIO_Init(SPI1_NSS_Port, &GPIO_InitStructure);

    GPIO_InitStructure.GPIO_Pin  = SPI1_SCK_Pin;                                  //SPI_SCK
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(SPI1_SCK_Port, &GPIO_InitStructure);

    GPIO_InitStructure.GPIO_Pin  = SPI1_MOSI_Pin;                                  //SPI_MOSI
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(SPI1_MOSI_Port, &GPIO_InitStructure);

    GPIO_InitStructure.GPIO_Pin  = SPI1_MISO_Pin;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;							//SPI_MISO
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;                               //Pull-up input
    GPIO_Init(SPI1_MISO_Port, &GPIO_InitStructure);

    SPI_InitStructure.SPI_Mode = SPI_Mode_Master;
    SPI_InitStructure.SPI_DataSize = SPI_DataSize_8b;
    SPI_InitStructure.SPI_DataWidth = SPI_DataWidth_8b;
    SPI_InitStructure.SPI_CPOL = SPI_CPOL_Low;
    SPI_InitStructure.SPI_CPHA = SPI_CPHA_1Edge;
    SPI_InitStructure.SPI_NSS = SPI_NSS_Soft;
    SPI_InitStructure.SPI_BaudRatePrescaler = SPI_BaudRatePrescaler_256;
    SPI_InitStructure.SPI_FirstBit = SPI_FirstBit_MSB;
    SPI_Init(SPI1, &SPI_InitStructure);

    NVIC_InitStructure.NVIC_IRQChannel = SPI1_IRQn;
    NVIC_InitStructure.NVIC_IRQChannelPriority = 1;
    NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
    NVIC_Init(&NVIC_InitStructure);

    SPI_ITConfig(SPI1, SPI_IT_RX | SPI_IT_TXEPT, ENABLE);
    SPI_BiDirectionalLineConfig(SPI1, SPI_Direction_Tx);
    SPI_BiDirectionalLineConfig(SPI1, SPI_Direction_Rx);
    SPI_Cmd(SPI1, ENABLE);

    return 0;
}

uint8_t spi_deinit(void)
{
	SPI_DeInit(SPI1);
	return 0;
}

uint8_t spi_write_read(uint8_t *in_buf, uint32_t in_len,
                                        uint8_t *out_buf, uint32_t out_len)
{
	GPIO_WriteBit(SPI1_NSS_Port, SPI1_NSS_Pin, RESET);
	if (in_len > 0)
		{
			for(uint32_t i = 0; i < in_len; i++){
		    	SPI_Read_Write_Byte(SPI1, in_buf[i]);
		    }
		}

	/* if out_len > 0 */
	if (out_len > 0)
		{
			for(uint32_t i = 0; i < out_len; i++)
		    	{
		    		out_buf[i] = SPI_Read_Write_Byte(SPI1, 0x00);
		    	}

		    }
	GPIO_WriteBit(SPI1_NSS_Port, SPI1_NSS_Pin, SET);
	return 0;
}
unsigned int SPI_Read_Write_Byte(SPI_TypeDef* SPIx, unsigned char tx_data)
{
	SPI_SendData(SPIx, tx_data);
	while(1) {
	    if(spi0_tx_flag == 1) {
	          spi0_tx_flag = 0;
	          break;
	    }
	}
	while (1) {
	     if(spi0_rx_flag == 1) {
	           spi0_rx_flag = 0;
	           return SPI_ReceiveData(SPIx);
	     }
	}
}

void SPI_handler(void)
{
    while(1) {
        if(SPI_GetITStatus(SPI1, SPI_IT_TXEPT)) {
            SPI_ClearITPendingBit(SPI1, SPI_IT_TXEPT);
            spi0_tx_flag = 1;
            break;
        }

        if(SPI_GetITStatus(SPI1, SPI_IT_RX)) {
            SPI_ClearITPendingBit(SPI1, SPI_IT_RX);                             //clear rx interrupt
            spi0_rx_flag = 1;
            break;
        }
    }
}

uint8_t reset_gpio_init(void)
{
	gpio_pin_configure(LORA_NRST_Port, LORA_NRST_Pin, GPIO_Mode_Out_PP);
    return 0;
}

uint8_t reset_gpio_deinit(void)
{
	return 0;
}

uint8_t reset_gpio_write(uint8_t data)
{
    if (data != 0)
    {
        /* set high */
    	GPIO_WriteBit(LORA_NRST_Port, LORA_NRST_Pin, SET);
    }
    else
    {
        /* set low */
    	GPIO_WriteBit(LORA_NRST_Port, LORA_NRST_Pin, RESET);
    }
    return 0;
}

uint8_t busy_gpio_init(void)
{
	gpio_pin_configure(LORA_BUSY_Port, LORA_BUSY_Pin, GPIO_Mode_IPD);
    return 0;
}

uint8_t busy_gpio_deinit(void)
{
	return 0;
}

uint8_t busy_gpio_read(uint8_t *value)
{
	*value = GPIO_ReadInputDataBit(LORA_BUSY_Port, LORA_BUSY_Pin);
    return 0;
}


void debug_print(const char *const fmt, ...)
{
	return;
}

void receive_callback(uint16_t type, uint8_t *buf, uint16_t len)
{
    switch (type)
    {
        case LLCC68_IRQ_TX_DONE :
        {
        	debug_print("llcc68: irq tx done.\n");

            break;
        }
        case LLCC68_IRQ_RX_DONE :
        {
        	debug_print("llcc68: irq rx done.\n");

            break;
        }
        case LLCC68_IRQ_PREAMBLE_DETECTED :
        {
        	debug_print("llcc68: irq preamble detected.\n");

            break;
        }
        case LLCC68_IRQ_SYNC_WORD_VALID :
        {
        	debug_print("llcc68: irq valid sync word detected.\n");

            break;
        }
        case LLCC68_IRQ_HEADER_VALID :
        {
        	debug_print("llcc68: irq valid header.\n");

            break;
        }
        case LLCC68_IRQ_HEADER_ERR :
        {
        	debug_print("llcc68: irq header error.\n");

            break;
        }
        case LLCC68_IRQ_CRC_ERR :
        {
        	debug_print("llcc68: irq crc error.\n");

            break;
        }
        case LLCC68_IRQ_CAD_DONE :
        {
        	debug_print("llcc68: irq cad done.\n");

            break;
        }
        case LLCC68_IRQ_CAD_DETECTED :
        {
        	debug_print("llcc68: irq cad detected.\n");

            break;
        }
        case LLCC68_IRQ_TIMEOUT :
        {
        	debug_print("llcc68: irq timeout.\n");

            break;
        }
        default :
        {
        	debug_print("llcc68: unknown code.\n");

            break;
        }
    }
}

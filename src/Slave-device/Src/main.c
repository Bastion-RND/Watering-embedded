/*
 * main.c
 */


#include "main.h"
#include <stdio.h>
#include <stdlib.h>

#include "HAL_conf.h"

#include "gpio.h"
#include "eeprom_in_flash.h"
//#include "lora_impl.h"
#include "lora_func.h"
//#include "driver_llcc68.h"

uint16_t ADCValue[ADC_SAMPLES_BUFFER_SIZE];
uint32_t HUMvalue = 0;
uint32_t BATvalue = 0;
uint32_t VREFvalue = 0;
uint32_t Voltage = 0;

void InitDelay();
void InitLed();


static __IO uint32_t TimingDelay;

static __IO uint32_t uwTick = 0;

void TimDoneInit()
{
	gpio_pin_configure(TIM_DONE_PORT, TIM_DONE_PIN, GPIO_Mode_Out_PP);
	GPIO_OUTPUT_RESET(TIM_DONE_PORT, TIM_DONE_PIN);
}


void InitLed()
{
	gpio_pin_configure(LED20_GPIO_PORT, LED20_GPIO_PIN, GPIO_Mode_Out_PP);
	gpio_pin_configure(LED40_GPIO_PORT, LED40_GPIO_PIN, GPIO_Mode_Out_PP);
	gpio_pin_configure(LED60_GPIO_PORT, LED60_GPIO_PIN, GPIO_Mode_Out_PP);
	gpio_pin_configure(LED80_GPIO_PORT, LED80_GPIO_PIN, GPIO_Mode_Out_PP);
	gpio_pin_configure(LED100_GPIO_PORT, LED100_GPIO_PIN, GPIO_Mode_Out_PP);
}


void LedToggling(GPIO_TypeDef * port, uint16_t pin, uint8_t times)
{
	for(uint8_t i = 0; i != times; i++){
		GPIO_WriteBit(port, pin, SET);
		delay_ms(200);
		GPIO_WriteBit(port, pin, RESET);
		delay_ms(200);
	}
}


uint8_t Check_RCC()
{
	FlagStatus powres = RCC_GetFlagStatus(RCC_FLAG_PORRST);
	FlagStatus lowres = RCC_GetFlagStatus(RCC_FLAG_LPWRRST);
	RCC_ClearFlag();
	if(powres)
	{
		LedToggling(LED20_GPIO_PORT, LED20_GPIO_PIN, 2);
		return HARD_RESET;
	}
	else if(lowres)
	{
		LedToggling(LED20_GPIO_PORT, LED20_GPIO_PIN, 1);
		return SOFT_RESET;
	}
	return OTHER_RESET;
}


void DMAInit(void)
{
    DMA_InitTypeDef DMA_InitStructure;
    NVIC_InitTypeDef NVIC_InitStruct;

    RCC_AHBPeriphClockCmd(RCC_AHBPeriph_DMA1, ENABLE);
    DMA_DeInit(DMA1_Channel1);
    DMA_InitStructure.DMA_PeripheralBaseAddr = (u32) & (ADC1->ADDATA);           //DMA transfer peripheral address
    DMA_InitStructure.DMA_MemoryBaseAddr = (u32)&ADCValue;                      //DMA transfer memory address
    DMA_InitStructure.DMA_DIR = DMA_DIR_PeripheralSRC;                          //DMA transfer direction from peripheral to memory
    DMA_InitStructure.DMA_BufferSize = ADC_SAMPLES_BUFFER_SIZE;                                       //DMA cache size
    DMA_InitStructure.DMA_PeripheralInc = DMA_PeripheralInc_Disable;            //After receiving the data, the peripheral address is forbidden to move backward
    DMA_InitStructure.DMA_MemoryInc = DMA_MemoryInc_Enable;                     //After receiving the data, the memory address is shifted backward
    DMA_InitStructure.DMA_PeripheralDataSize = DMA_PeripheralDataSize_HalfWord; //Define the peripheral data width to 16 bits
    DMA_InitStructure.DMA_MemoryDataSize = DMA_MemoryDataSize_HalfWord;         //Define the memory data width to 16 bits
    DMA_InitStructure.DMA_Mode = DMA_Mode_Normal;                             //Cycle conversion mode
    DMA_InitStructure.DMA_Priority = DMA_Priority_High;                         //DMA priority is high
    DMA_InitStructure.DMA_M2M = DMA_M2M_Disable;                                //M2M mode is disabled
    DMA_Init(DMA1_Channel1, &DMA_InitStructure);
    DMA_Cmd(DMA1_Channel1, ENABLE);

    DMA_ITConfig(DMA1_Channel1, DMA_IT_TC, ENABLE);                              //DMA interrupt initialization
    NVIC_InitStruct.NVIC_IRQChannel = DMA1_Channel1_IRQn;
    NVIC_InitStruct.NVIC_IRQChannelPriority = 0;
    NVIC_InitStruct.NVIC_IRQChannelCmd = ENABLE;
    NVIC_Init(&NVIC_InitStruct);
}

void InitADC()
{
	gpio_pin_configure(SOIL_HUMIDITY_PORT, SOIL_HUMIDITY_PIN, GPIO_Mode_AIN);
	gpio_pin_configure(BATTERY_MEAS_PORT, BATTERY_MEAS_PIN, GPIO_Mode_AIN);

	ADC_InitTypeDef  ADC_InitStructure;
	ADC_StructInit(&ADC_InitStructure);

	RCC_APB2PeriphClockCmd(RCC_APB2Periph_ADC1, ENABLE);                         //Enable ADC clock

	ADC_InitStructure.ADC_Resolution = ADC_Resolution_12b;
	ADC_InitStructure.ADC_PRESCARE = ADC_PCLK2_PRESCARE_16;                     //ADC prescale factor
	ADC_InitStructure.ADC_Mode = ADC_Mode_Continuous_Scan;                      //Set ADC mode to single conversion mode
	ADC_InitStructure.ADC_DataAlign = ADC_DataAlign_Right;                      //AD data right-justified
	ADC_InitStructure.ADC_ExternalTrigConv = ADC_ExternalTrigConv_T1_CC1;
	ADC_Init(ADC1, &ADC_InitStructure);

	ADC_RegularChannelConfig(ADC1, ADC_Channel_0, 0, ADC_SampleTime_239_5Cycles);
	ADC_RegularChannelConfig(ADC1, ADC_Channel_1, 0, ADC_SampleTime_239_5Cycles);
	ADC_RegularChannelConfig(ADC1, ADC_Channel_Vrefint, 0, ADC_SampleTime_239_5Cycles);//Enable the channel
	ADC_VrefintCmd(ENABLE);

    ADC_DMACmd(ADC1, ENABLE);                                                    //Enable ADCDMA
    ADC_Cmd(ADC1, ENABLE);                                                       //Enable AD conversion

}

static uint16_t ADC_filter(uint16_t* pData, int num, int off, int count)
{
  uint32_t result = 0;

  for( int i = 0; i < count; i++ ) {
    result += pData[i * num + off];
  }
  result /= count;

  return result;
}

static int voltage_calc(uint32_t raw, int vdda)
{
  return raw * ADC_VDDA / vdda;
}

static int voltage_ref(uint32_t raw, int vdda)
{
  return raw * vdda / 1200;
}


uint8_t Approx_HUM(uint16_t hum, DeviceConfig_t conf)
{
	if (hum > 0)
	{
		if (hum <= (conf.soil_humidity_MAX * 0.11))
		{
			return (uint8_t) ((hum * 20) / (conf.soil_humidity_MAX * 0.11));
		}
		else if (hum >= (conf.soil_humidity_MAX * 0.89))
		{
			return ((uint8_t) ((hum * 20) / (conf.soil_humidity_MAX * 0.11)) - 82);
		}
		else
		{
			return ((uint8_t) ((hum * 60) / (conf.soil_humidity_MAX - conf.soil_humidity_MAX * 0.11 * 2)) + 20);
		}
	}
	return 0;
}

#define BATTERY_MAX_MV 4500
#define BATTERY_MIN_MV 2700

uint8_t Approx_BAT(uint16_t bat)
{
	return (uint8_t)((((bat*2) - BATTERY_MIN_MV) * 100) / (BATTERY_MAX_MV - BATTERY_MIN_MV));
}

uint32_t CRC_MCU_ID()
{
	uint32_t* ID = (uint32_t*)MCU_UID_ADDRESS;
	uint32_t CRCValue = 0;
	RCC_AHBPeriphClockCmd(RCC_AHBPeriph_CRC, ENABLE);
	CRC_ResetDR();
	        /* Compute the CRC of "DataBuffer" */
	CRCValue = CRC_CalcBlockCRC(ID, 3);
	return CRCValue;
}


LoraPackage_t ToPackage(LoraPackage_t package, uint16_t hum, uint16_t bat, DeviceConfig_t conf)
{
	uint32_t ID = CRC_MCU_ID();
	package.MCU_ID[0] = (uint8_t)((ID & 0xFF000000) >> 24);
	package.MCU_ID[1] = (uint8_t)((ID & 0x00FF0000) >> 16);
	package.MCU_ID[2] = (uint8_t)((ID & 0x0000FF00) >> 8);
	package.MCU_ID[3] = (uint8_t)((ID & 0x000000FF) >> 0);

	package.battery_percent =  Approx_BAT(bat);
	if (package.battery_percent < 40)
	{
		hum = (uint16_t)(hum * 1.2);
	}
	if (package.battery_percent > 100)
	{
		package.battery_percent = 100;
	}
	package.soil_humidity = Approx_HUM(hum, conf);
	if (package.soil_humidity > 100)
	{
		package.soil_humidity = 100;
	}

	return package;
}

void Check_HUM(uint8_t hum)
{
	if ((hum <= 100) && hum > 80)
	{
		LedToggling(LED100_GPIO_PORT, LED100_GPIO_PIN, 5);
	}
	else if ((hum <= 80) && hum > 60)
	{
		LedToggling(LED80_GPIO_PORT, LED80_GPIO_PIN, 5);
	}
	else if ((hum <= 60) && hum > 40)
	{
		LedToggling(LED60_GPIO_PORT, LED60_GPIO_PIN, 5);
	}
	else if ((hum <= 40) && hum > 20)
	{
		LedToggling(LED40_GPIO_PORT, LED40_GPIO_PIN, 5);
	}
	else
	{
		LedToggling(LED20_GPIO_PORT, LED20_GPIO_PIN, 5);
	}
}



BootStatus boot_mode;
uint8_t lora_start = 0;

#define CONFIG_EEPROM_ADDRESS 42
#define DEFAULT_SOIL_HUMIDITY_MIN 150
#define DEFAULT_SOIL_HUMIDITY_MAX 2000

DeviceConfig_t Config;
LoraPackage_t Package;



int main()
{
	SysTick_Config(SystemCoreClock / FREQUENCY_HZ);
	InitDelay();
	InitLed();
	TimDoneInit();
	EepromInFlash.init();

	boot_mode = Check_RCC();
	EepromInFlash.read(CONFIG_EEPROM_ADDRESS, Config.u8, sizeof(DeviceConfig_t));

	if (boot_mode == HARD_RESET)
		{
			Config.boot_count = Config.boot_count + 1;
			if(Config.soil_humidity_MAX == 0) {
				Config.soil_humidity_MAX = DEFAULT_SOIL_HUMIDITY_MAX;
				EepromInFlash.write(CONFIG_EEPROM_ADDRESS, Config.u8, sizeof(DeviceConfig_t));
				lora_start = 1;
				txen_init();
				lora_init();
				dio1_interrupt_init();
			}
		}

	DMAInit();
	InitADC();
	ADC_SoftwareStartConvCmd(ADC1, ENABLE);

	while (Voltage == 0){}

	if (HUMvalue > Config.soil_humidity_MAX)
	{
		Config.soil_humidity_MAX = HUMvalue;
	}

	Package = ToPackage(Package, HUMvalue, BATvalue, Config);
	Check_HUM(Package.soil_humidity);

	if ((Config.boot_count % 4 != 0) && (Config.soil_humidity_LAST == Package.soil_humidity))
	{
		GPIO_WriteBit(TIM_DONE_PORT, TIM_DONE_PIN, SET);
	}
	else
	{
		Config.soil_humidity_LAST = Package.soil_humidity;
		EepromInFlash.write(CONFIG_EEPROM_ADDRESS, Config.u8, sizeof(DeviceConfig_t));
		if (lora_start == 0)
		{
			txen_init();
			lora_init();
			dio1_interrupt_init();
		}
		lora_sent(Package.u8, sizeof(LoraPackage_t));
		LedToggling(LED60_GPIO_PORT, LED60_GPIO_PIN, 3);
	}
	GPIO_WriteBit(TIM_DONE_PORT, TIM_DONE_PIN, SET);
//	uint8_t payload[6];
	while (1)
	{
////		lora_sent(Package.u8, sizeof(LoraPackage_t));
////		Package.MCU_ID = 0x01234567;
////		Package.soil_humidity = 0x89;
////		payload[0] = (uint8_t)((Package.MCU_ID & 0xFF000000) >> 24);
////		payload[1] = (uint8_t)((Package.MCU_ID & 0x00FF0000) >> 16);
////		payload[2] = (uint8_t)((Package.MCU_ID & 0x0000FF00) >> 8);
////		payload[3] = (uint8_t)((Package.MCU_ID & 0x000000FF) >> 0);
////		payload[4] = Package.soil_humidity;
////		payload[5] = Package.battery_percent;
//
////		lora_sent(Package.u8, sizeof(LoraPackage_t));
////		lora_sent(payload, 6);
		delay_ms(1000);
		LedToggling(LED60_GPIO_PORT, LED60_GPIO_PIN, 3);
	}
}


void DMA1_Channel1_IRQHandler(void)
{
    ADC_SoftwareStartConvCmd(ADC1, DISABLE);                                     //Stop Conversion
    DMA_ClearITPendingBit(DMA1_IT_TC1);                                          //Clear interrupt flag
    ADC_DeInit(ADC1);

    VREFvalue = ADC_filter(ADCValue, 3, 2, 64);
    Voltage = voltage_ref(VREFvalue, ADC_VDDA);

    HUMvalue = ADC_filter(ADCValue, 3, 0, 64);
    HUMvalue = voltage_calc(HUMvalue, Voltage);

    BATvalue = ADC_filter(ADCValue, 3, 1, 64);
    BATvalue = voltage_calc(BATvalue, Voltage);
}

void EXTI2_3_IRQHandler(void)
{
	dio1_irq_handler();
	EXTI_ClearFlag(EXTI_Line2);                                                 //���EXTI0��·����λ
}


void SPI1_IRQHandler (void)
{
	SPI_handler();
}

// ----- SysTick_Handler() ----------------------------------------------------

//extern "C"
void SysTick_Handler(void)
{
	uwTick += 1;

    if (TimingDelay != 0x00) {
        TimingDelay--;
    }
}


void InitDelay()
{
    if (SysTick_Config(SystemCoreClock / FREQUENCY_HZ)) {
        /* Capture error */
        while (1) {}
    }

    /* Configure the SysTick handler priority */
    NVIC_SetPriority(SysTick_IRQn, 0x0);
}


void delay_ms(__IO uint32_t nTime)
{
    TimingDelay = nTime;

    while (TimingDelay != 0)
        ;
}

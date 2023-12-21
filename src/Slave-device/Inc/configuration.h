/* LED */
#define LED20_GPIO_PORT     GPIOB
#define LED20_GPIO_PIN      GPIO_Pin_3

#define LED40_GPIO_PORT     GPIOB
#define LED40_GPIO_PIN      GPIO_Pin_4

#define LED60_GPIO_PORT     GPIOB
#define LED60_GPIO_PIN      GPIO_Pin_5

#define LED80_GPIO_PORT     GPIOB
#define LED80_GPIO_PIN      GPIO_Pin_6

#define LED100_GPIO_PORT    GPIOB
#define LED100_GPIO_PIN     GPIO_Pin_7

/* ADC */
#define SOIL_HUMIDITY_PORT GPIOA
#define SOIL_HUMIDITY_PIN  GPIO_Pin_0

#define BATTERY_MEAS_PORT  GPIOA
#define BATTERY_MEAS_PIN   GPIO_Pin_1

#define ADC_CHANNELS_COUNT      3
#define ADC_SAMPLES_COUNT       64
#define ADC_SAMPLES_BUFFER_SIZE (ADC_CHANNELS_COUNT * ADC_SAMPLES_COUNT)
#define ADC_VDDA                3300 /* mV */

#define VOLTAGE_DIVIDER_R1      10000 /* R7, R13 - 5k6 */
#define VOLTAGE_DIVIDER_R2      10000 /* R8, R15 - 2k */
#define VOLTAGE_COEFFICIENT     ((int) (VOLTAGE_DIVIDER_R1 + VOLTAGE_DIVIDER_R2) / VOLTAGE_DIVIDER_R2)

/* TIMDONE */
#define TIM_DONE_PORT GPIOA
#define TIM_DONE_PIN  GPIO_Pin_8

/* SPI LORA */
#define SPI1_NSS_Pin GPIO_Pin_4
#define SPI1_NSS_Port GPIOA

#define SPI1_SCK_Pin GPIO_Pin_5
#define SPI1_SCK_Port GPIOA

#define SPI1_MOSI_Pin GPIO_Pin_7
#define SPI1_MOSI_Port GPIOA

#define SPI1_MISO_Pin GPIO_Pin_6
#define SPI1_MISO_Port GPIOA

#define LORA_NRST_Pin GPIO_Pin_11
#define LORA_NRST_Port GPIOA

#define LORA_BUSY_Pin GPIO_Pin_0
#define LORA_BUSY_Port GPIOB

#define LORA_DIO1_PIN GPIO_Pin_2
#define LORA_DIO1_PORT GPIOA

#define LORA_TXEN_PIN GPIO_Pin_1
#define LORA_TXEN_PORT GPIOB


void delay_ms(__IO uint32_t nTime);

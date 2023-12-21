/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef GPIO_H
#define GPIO_H

/* Includes ------------------------------------------------------------------*/
#include "HAL_conf.h"
#include "HAL_gpio.h"

/* Macro ---------------------------------------------------------------------*/
#define IS_GPIO_INPUT_SET(g, p)   (GPIO_ReadInputDataBit(g, p) == Bit_SET)

#define GPIO_OUTPUT_SET(g, p)     (GPIO_WriteBit(g, p, Bit_SET))
#define GPIO_OUTPUT_RESET(g, p)   (GPIO_WriteBit(g, p, Bit_RESET))
#define GPIO_OUTPUT_TOGGLE(g, p)  (GPIO_ReadOutputDataBit(g, p)? \
                                   GPIO_OUTPUT_RESET(g, p) : GPIO_OUTPUT_SET(g, p))
#ifdef __cplusplus
extern "C" {
#endif

/* Prototypes ----------------------------------------------------------------*/
void gpio_periphClock_cmd(GPIO_TypeDef *, FunctionalState);
void gpio_pin_configure(GPIO_TypeDef *, uint16_t, GPIOMode_TypeDef);


#ifdef __cplusplus
}
#endif

#endif /* __LIB_GPIO_H */

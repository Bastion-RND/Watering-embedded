#include "gpio.h"

void gpio_periphClock_cmd(GPIO_TypeDef *GPIOx, FunctionalState NewState)
{
    uint32_t RCC_AHBPeriph;

    if (GPIOx == GPIOA) {
        RCC_AHBPeriph = RCC_AHBPeriph_GPIOA;
    }
    else if (GPIOx == GPIOB) {
        RCC_AHBPeriph = RCC_AHBPeriph_GPIOB;
    }
    else if (GPIOx == GPIOB) {
        RCC_AHBPeriph = RCC_AHBPeriph_GPIOC;
    }
    else if (GPIOx == GPIOB) {
        RCC_AHBPeriph = RCC_AHBPeriph_GPIOD;
    }
    else {
        RCC_AHBPeriph = 0;
    }

    RCC_AHBPeriphClockCmd(RCC_AHBPeriph, NewState);
}

void gpio_pin_configure(GPIO_TypeDef *GPIOx, uint16_t GPIO_Pin, GPIOMode_TypeDef GPIO_Mode)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    GPIO_StructInit(&GPIO_InitStructure);

    gpio_periphClock_cmd(GPIOx, ENABLE);

    GPIO_InitStructure.GPIO_Pin = GPIO_Pin;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOx, &GPIO_InitStructure);
}

/**
 * Copyright (c) 2015 - present LibDriver All rights reserved
 * 
 * The MIT License (MIT)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE. 
 *
 * @file      driver_llcc68_lora.c
 * @brief     driver llcc68 lora source file
 * @version   1.0.0
 * @author    Shifeng Li
 * @date      2023-04-15
 *
 * <h3>history</h3>
 * <table>
 * <tr><th>Date        <th>Version  <th>Author      <th>Description
 * <tr><td>2023/04/15  <td>1.0      <td>Shifeng Li  <td>first upload
 * </table>
 */

#include <lora_func.h>
#include "configuration.h"
#include "HAL_conf.h"
#include "HAL_gpio.h"
#include "gpio.h"

static llcc68_handle_t gs_handle;        /**< llcc68 handle */
//static uint8_t gs_sent_buffer[256];
/**
 * @brief  llcc68 lora irq
 * @return status code
 *         - 0 success
 *         - 1 run failed
 * @note   none
 */
uint8_t lora_irq_handler(void)
{
    if (llcc68_irq_handler(&gs_handle) != 0)
    {
        return 1;
    }
    else
    {
        return 0;
    }
}

/**
 * @brief     lora example init
 * @param[in] *callback points to a callback address
 * @return    status code
 *            - 0 success
 *            - 1 init failed
 * @note      none
 */
uint8_t lora_init()
{
    uint32_t reg;
    uint8_t status;
    uint8_t val;
//    uint16_t error;


    /* link interface function */
    DRIVER_LLCC68_LINK_INIT(&gs_handle, llcc68_handle_t);
    DRIVER_LLCC68_LINK_SPI_INIT(&gs_handle, spi_init);
    DRIVER_LLCC68_LINK_SPI_DEINIT(&gs_handle, spi_deinit);
    DRIVER_LLCC68_LINK_SPI_WRITE_READ(&gs_handle, spi_write_read);
    DRIVER_LLCC68_LINK_RESET_GPIO_INIT(&gs_handle, reset_gpio_init);
    DRIVER_LLCC68_LINK_RESET_GPIO_DEINIT(&gs_handle, reset_gpio_deinit);
    DRIVER_LLCC68_LINK_RESET_GPIO_WRITE(&gs_handle, reset_gpio_write);
    DRIVER_LLCC68_LINK_BUSY_GPIO_INIT(&gs_handle, busy_gpio_init);
    DRIVER_LLCC68_LINK_BUSY_GPIO_DEINIT(&gs_handle, busy_gpio_deinit);
    DRIVER_LLCC68_LINK_BUSY_GPIO_READ(&gs_handle, busy_gpio_read);
    DRIVER_LLCC68_LINK_DELAY_MS(&gs_handle, delay_ms);
    DRIVER_LLCC68_LINK_DEBUG_PRINT(&gs_handle, debug_print);
    DRIVER_LLCC68_LINK_RECEIVE_CALLBACK(&gs_handle, receive_callback);
    
    //GPIO_WriteBit(SPI1_NSS_Port, SPI1_NSS_Pin, RESET);
    llcc68_init(&gs_handle);

    llcc68_get_tx_clamp_config(&gs_handle, &val);
    val = val | 0x1E;
    llcc68_set_tx_clamp_config(&gs_handle, val);

    llcc68_set_regulator_mode(&gs_handle, LLCC68_REGULATOR_MODE_DC_DC_LDO);
    llcc68_set_dio3_as_tcxo_ctrl(&gs_handle, LLCC68_TCXO_VOLTAGE_3P3V, 10);
    llcc68_set_standby(&gs_handle, LLCC68_CLOCK_SOURCE_XTAL_32MHZ);
    uint16_t timeout = 10;
    while(1)
    {
    	llcc68_get_status(&gs_handle, &status);
    	status = status & 0x70;
    	if (status == 0x30)
    	{
    		break;
    	}
    	timeout--;
    	if (timeout == 0)
    	{
    		break;
    	}
    }
//    llcc68_get_device_errors(&gs_handle, &error);
    llcc68_clear_device_errors(&gs_handle);
    llcc68_set_xta_trim(&gs_handle, 0x1C);
    llcc68_set_xtb_trim(&gs_handle, 0x1C);

//    llcc68_set_dio2_as_rf_switch_ctrl(&gs_handle, 1);


    llcc68_set_buffer_base_address(&gs_handle, 0x00, 0x00);
    llcc68_set_packet_type(&gs_handle, LLCC68_PACKET_TYPE_LORA);

    llcc68_set_lora_modulation_params(&gs_handle, LORA_DEFAULT_SF,
                		LORA_DEFAULT_BANDWIDTH, LORA_DEFAULT_CR, LLCC68_BOOL_FALSE);
    llcc68_set_lora_sync_word(&gs_handle, LORA_DEFAULT_SYNC_WORD);
    llcc68_set_lora_packet_params(&gs_handle, LORA_DEFAULT_PREAMBLE_LENGTH, LORA_DEFAULT_HEADER,
            		LORA_DEFAULT_BUFFER_SIZE, LORA_DEFAULT_CRC_TYPE, LORA_DEFAULT_INVERT_IQ);

    llcc68_get_iq_polarity(&gs_handle, &val);
    val |= (1 << 2);
    llcc68_set_iq_polarity(&gs_handle, val);

    llcc68_set_calibration(&gs_handle, 0xFF);
    llcc68_set_calibration_image(&gs_handle, 0xD7, 0xD8);

    llcc68_set_standby(&gs_handle, LLCC68_CLOCK_SOURCE_XTAL_32MHZ);
    llcc68_set_xta_trim(&gs_handle, 0x1C);
    llcc68_set_xtb_trim(&gs_handle, 0x1C);
    reg = (uint32_t)(868000000U * 1.048576);
//    llcc68_frequency_convert_to_register(&gs_handle, 868000000U, (uint32_t *)&reg);
    llcc68_set_rf_frequency(&gs_handle, reg);

    llcc68_set_pa_config(&gs_handle, LORA_DEFAULT_PA_CONFIG_DUTY_CYCLE, LORA_DEFAULT_PA_CONFIG_HP_MAX);
    llcc68_set_ocp(&gs_handle, 0x38);
    llcc68_set_tx_params(&gs_handle, LORA_DEFAULT_TX_DBM, LORA_DEFAULT_RAMP_TIME);

    return 0;
}

/**
 * @brief     lora example sent lora data
 * @param[in] *buf points to a data buffer
 * @param[in] len is the data length
 * @return    status code
 *            - 0 success
 *            - 1 sent failed
 * @note      none
 */
uint8_t lora_sent(uint8_t *buf, uint16_t len)
{
//    uint16_t error;
	uint8_t val;
    llcc68_set_lora_packet_params(&gs_handle, LORA_DEFAULT_PREAMBLE_LENGTH, LORA_DEFAULT_HEADER,
    		len, LORA_DEFAULT_CRC_TYPE, LORA_DEFAULT_INVERT_IQ);

    llcc68_get_iq_polarity(&gs_handle, &val);
    val |= (1 << 2);
    llcc68_set_iq_polarity(&gs_handle, val);

    llcc68_write_buffer(&gs_handle, 0x00, buf, len);
    txen_write(1);

    llcc68_set_standby(&gs_handle, LLCC68_CLOCK_SOURCE_XTAL_32MHZ);
    llcc68_set_xta_trim(&gs_handle, 0x1C);
    llcc68_set_xtb_trim(&gs_handle, 0x1C);

    llcc68_set_dio_irq_params(&gs_handle, LLCC68_IRQ_TX_DONE | LLCC68_IRQ_TIMEOUT, LLCC68_IRQ_TX_DONE | LLCC68_IRQ_TIMEOUT, 0x0000, 0x0000);
//    llcc68_clear_device_errors(&gs_handle);
    llcc68_clear_irq_status(&gs_handle, 0x03FF);

    llcc68_get_tx_modulation(&gs_handle, &val);
    val = val & 0xFB;
    llcc68_set_tx_modulation(&gs_handle, val);

    llcc68_set_tx(&gs_handle, 0);

    uint16_t timeout = 10000;
    while(1)
    {
    	if (gs_handle.tx_done == 1)
    	{
    		break;
    	}
    	timeout--;
    	if (timeout == 0)
    	{
    		break;
    	}
    }
    return 0;
}


/**
 * @brief  lora example deinit
 * @return status code
 *         - 0 success
 *         - 1 deinit failed
 * @note   none
 */
uint8_t lora_deinit(void)
{
    if (llcc68_deinit(&gs_handle) != 0)
    {
        return 1;
    }
    else
    {
        return 0;
    }
}

/**
 * @brief  lora example enter to the sleep mode
 * @return status code
 *         - 0 success
 *         - 1 sleep failed
 * @note   none
 */
uint8_t lora_sleep(void)
{
    if (llcc68_set_sleep(&gs_handle, LORA_DEFAULT_START_MODE, LORA_DEFAULT_RTC_WAKE_UP) != 0)
    {
        return 1;
    }
    else
    {
        return 0;
    }
}

/**
 * @brief  lora example wake up the chip
 * @return status code
 *         - 0 success
 *         - 1 wake up failed
 * @note   none
 */
uint8_t lora_wake_up(void)
{
    uint8_t status;
    
    if (llcc68_get_status(&gs_handle, (uint8_t *)&status) != 0)
    {
        return 1;
    }
    else
    {
        return 0;
    }
}

///**
// * @brief  lora example enter to the continuous receive mode
// * @return status code
// *         - 0 success
// *         - 1 enter failed
// * @note   none
// */
//uint8_t lora_set_continuous_receive_mode(void)
//{
//    uint8_t setup;
//
//    /* set dio irq */
//    if (llcc68_set_dio_irq_params(&gs_handle, LLCC68_IRQ_RX_DONE | LLCC68_IRQ_TIMEOUT | LLCC68_IRQ_CRC_ERR | LLCC68_IRQ_CAD_DONE | LLCC68_IRQ_CAD_DETECTED,
//                                  LLCC68_IRQ_RX_DONE | LLCC68_IRQ_TIMEOUT | LLCC68_IRQ_CRC_ERR | LLCC68_IRQ_CAD_DONE | LLCC68_IRQ_CAD_DETECTED,
//                                  0x0000, 0x0000) != 0)
//    {
//        return 1;
//    }
//
//    /* clear irq status */
//    if (llcc68_clear_irq_status(&gs_handle, 0x03FFU) != 0)
//    {
//        return 1;
//    }
//
//    /* set lora packet params */
//    if (llcc68_set_lora_packet_params(&gs_handle, LORA_DEFAULT_PREAMBLE_LENGTH,
//                                      LORA_DEFAULT_HEADER, LORA_DEFAULT_BUFFER_SIZE,
//                                      LORA_DEFAULT_CRC_TYPE, LORA_DEFAULT_INVERT_IQ) != 0)
//    {
//        return 1;
//    }
//
//    /* get iq polarity */
//    if (llcc68_get_iq_polarity(&gs_handle, (uint8_t *)&setup) != 0)
//    {
//        return 1;
//    }
//
//#if LLCC68_LORA_DEFAULT_INVERT_IQ == LLCC68_BOOL_FALSE
//    setup |= 1 << 2;
//#else
//    setup &= ~(1 << 2);
//#endif
//
//    /* set the iq polarity */
//    if (llcc68_set_iq_polarity(&gs_handle, setup) != 0)
//    {
//        return 1;
//    }
//
//    /* start receive */
//    if (llcc68_continuous_receive(&gs_handle) != 0)
//    {
//        return 1;
//    }
//
//    return 0;
//}
//
///**
// * @brief  lora example enter to the shot receive mode
// * @return status code
// *         - 0 success
// *         - 1 enter failed
// * @note   none
// */
//uint8_t lora_set_shot_receive_mode(double us)
//{
//    uint8_t setup;
//
//    /* set dio irq */
//    if (llcc68_set_dio_irq_params(&gs_handle, LLCC68_IRQ_RX_DONE | LLCC68_IRQ_TIMEOUT | LLCC68_IRQ_CRC_ERR | LLCC68_IRQ_CAD_DONE | LLCC68_IRQ_CAD_DETECTED,
//                                  LLCC68_IRQ_RX_DONE | LLCC68_IRQ_TIMEOUT | LLCC68_IRQ_CRC_ERR | LLCC68_IRQ_CAD_DONE | LLCC68_IRQ_CAD_DETECTED,
//                                  0x0000, 0x0000) != 0)
//    {
//        return 1;
//    }
//
//    /* clear irq status */
//    if (llcc68_clear_irq_status(&gs_handle, 0x03FFU) != 0)
//    {
//        return 1;
//    }
//
//    /* set lora packet params */
//    if (llcc68_set_lora_packet_params(&gs_handle, LORA_DEFAULT_PREAMBLE_LENGTH,
//                                      LORA_DEFAULT_HEADER, LORA_DEFAULT_BUFFER_SIZE,
//                                      LORA_DEFAULT_CRC_TYPE, LORA_DEFAULT_INVERT_IQ) != 0)
//    {
//        return 1;
//    }
//
//    /* get iq polarity */
//    if (llcc68_get_iq_polarity(&gs_handle, (uint8_t *)&setup) != 0)
//    {
//        return 1;
//    }
//
//#if LLCC68_LORA_DEFAULT_INVERT_IQ == LLCC68_BOOL_FALSE
//    setup |= 1 << 2;
//#else
//    setup &= ~(1 << 2);
//#endif
//
//    /* set the iq polarity */
//    if (llcc68_set_iq_polarity(&gs_handle, setup) != 0)
//    {
//        return 1;
//    }
//
//    /* start receive */
//    if (llcc68_single_receive(&gs_handle, us) != 0)
//    {
//        return 1;
//    }
//
//    return 0;
//}

void dio1_irq_handler()
{
	llcc68_irq_handler(&gs_handle);
}

//void lora_recieve_data(uint8_t *res)
//{
//	res = gs_handle.receive_buf;
//}

void lora_check_irq(uint16_t *status)
{
	llcc68_get_irq_status(&gs_handle, status);
}


///**
// * @brief  lora example enter to the sent mode
// * @return status code
// *         - 0 success
// *         - 1 enter failed
// * @note   none
// */
//uint8_t lora_set_sent_mode(void)
//{
//    /* set dio irq */
//
//	llcc68_set_dio_irq_params(&gs_handle,  0x0202, 0x0000, 0x0202, 0x0000);
////    if (llcc68_set_dio_irq_params(&gs_handle, LLCC68_IRQ_TX_DONE | LLCC68_IRQ_TIMEOUT | LLCC68_IRQ_CAD_DONE | LLCC68_IRQ_CAD_DETECTED,
////                                  LLCC68_IRQ_TX_DONE | LLCC68_IRQ_TIMEOUT | LLCC68_IRQ_CAD_DONE | LLCC68_IRQ_CAD_DETECTED,
////                                  0x0000, 0x0000) != 0)
////    {
////        return 1;
////    }
////
//    /* clear irq status */
//    if (llcc68_clear_irq_status(&gs_handle, 0x03FFU) != 0)
//    {
//        return 1;
//    }
//
//    return 0;
//}



///**
// * @brief      lora example run the cad
// * @param[out] *enable points to a enable buffer
// * @return     status code
// *             - 0 success
// *             - 1 run failed
// * @note       none
// */
//uint8_t lora_run_cad(llcc68_bool_t *enable)
//{
//    /* set cad params */
//    if (llcc68_set_cad_params(&gs_handle, LORA_DEFAULT_CAD_SYMBOL_NUM,
//                              LORA_DEFAULT_CAD_DET_PEAK, LORA_DEFAULT_CAD_DET_MIN,
//                              LLCC68_LORA_CAD_EXIT_MODE_ONLY, 0) != 0)
//    {
//        return 1;
//    }
//
//    /* run the cad */
//    if (llcc68_lora_cad(&gs_handle, enable) != 0)
//    {
//        return 1;
//    }
//
//    return 0;
//}

/**
 * @brief      lora example get the status
 * @param[out] *rssi points to a rssi buffer
 * @param[out] *snr points to a snr buffer
 * @return     status code
 *             - 0 success
 *             - 1 get status failed
 * @note       none
 */
uint8_t lora_get_status(float *rssi, float *snr)
{
    uint8_t rssi_pkt_raw;
    uint8_t snr_pkt_raw;
    uint8_t signal_rssi_pkt_raw;
    float signal_rssi_pkt;
    
    /* get the status */
    if (llcc68_get_lora_packet_status(&gs_handle, (uint8_t *)&rssi_pkt_raw, (uint8_t *)&snr_pkt_raw,
                                     (uint8_t *)&signal_rssi_pkt_raw, (float *)rssi, (float *)snr, (float *)&signal_rssi_pkt) != 0)
    {
        return 1;
    }
    
    return 0;
}

/**
 * @brief      lora example check packet error
 * @param[out] *enable points to a bool value buffer
 * @return     status code
 *             - 0 success
 *             - 1 check packet error failed
 * @note       none
 */
uint8_t lora_check_packet_error(llcc68_bool_t *enable)
{
    /* check the error */
    if (llcc68_check_packet_error(&gs_handle, enable) != 0)
    {
        return 1;
    }

    return 0;
}

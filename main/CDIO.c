#include <stdio.h>
#include <sys/socket.h>
#include "rtc_wdt.h"
#include "driver/uart.h"

#include "EZADC.h"

#include "rgb_led.h"

#include "EZWIFI.h"

rgb_led MY_LED;

char *data = (char *) "1\n";

void socket_transmitter_sta_loop(bool (*is_wifi_connected)()) {
    int socket_fd = -1;
    while (1) {
        close(socket_fd);
        char *ip = (char *) "192.168.4.1";
        struct sockaddr_in caddr;
        caddr.sin_family = AF_INET;
        caddr.sin_port = htons(2223);
        while (!is_wifi_connected()) {
            // wait until connected to AP
            printf("wifi not connected. waiting...\n");
            vTaskDelay(1000 / portTICK_PERIOD_MS);
        }
        printf("initial wifi connection established.\n");
        if (inet_aton(ip, &caddr.sin_addr) == 0) {
            printf("ERROR: inet_aton\n");
            continue;
        }

        socket_fd = socket(PF_INET, SOCK_DGRAM, 0);
        if (socket_fd == -1) {
            printf("ERROR: Socket creation error [%s]\n", strerror(errno));
            continue;
        }
        if (connect(socket_fd, (const struct sockaddr *) &caddr, sizeof(struct sockaddr)) == -1) {
            printf("ERROR: socket connection error [%s]\n", strerror(errno));
            continue;
        }

        printf("sending frames.\n");
		int i = 0;
        while (1) {
            //double start_time = get_steady_clock_timestamp();
            if (!is_wifi_connected()) {
                printf("ERROR: wifi is not connected\n");
                break;
            }

            if (sendto(socket_fd, &data, strlen(data), 0, (const struct sockaddr *) &caddr, sizeof(caddr)) !=
                strlen(data)) {
                vTaskDelay(1);
                continue;				
            }

            vTaskDelay(pdMS_TO_TICKS(100));

            //double end_time = get_steady_clock_timestamp();
            //lag = end_time - start_time;
        }
    }
}

/* TaskHandle_t xHandle = NULL; */

/* void vTask_socket_transmitter_sta_loop(void *pvParamteres) { */
/*     for(;;) { */
/* 	socket_transmitter_sta_loop(&is_wifi_connected); */
/*     } */
/* } */

static void echo_task(void *arg)
{
    /* Configure parameters of an UART driver,
     * communication pins and install the driver */
    uart_config_t uart_config = {
        .baud_rate = 921600,
        .data_bits = UART_DATA_8_BITS,
        .parity    = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    int intr_alloc_flags = 0;

    ESP_ERROR_CHECK(uart_driver_install(0, 3072 * 2, 0, 0, NULL, intr_alloc_flags));
    ESP_ERROR_CHECK(uart_param_config(0, &uart_config));

    // Configure a temporary buffer for the incoming data
    uint8_t *uart_data = (uint8_t *) malloc(3072);

    while (1) {
        // Read data from the UART
        int len = uart_read_bytes(0, uart_data, (3072 - 1), 20 / portTICK_PERIOD_MS);
        // Write data back to the UART
        //uart_write_bytes(0, (const char *) uart_data, len);
		
        if (len) {
            uart_data[len] = '\0';
            //ESP_LOGI(TAG, "Recv str: %s", (char *) uart_data);
			
			if (strcmp((char *) uart_data, "red") == 0)
			{
				rgb_set_color(&MY_LED, rgb_red);
			}
			else if (strcmp((char *) uart_data, "blue") == 0)
			{
				rgb_set_color(&MY_LED, rgb_blue);
			}
			else if (strcmp((char *) uart_data, "green") == 0)
			{
				rgb_set_color(&MY_LED, rgb_green);
			}
			else if (strcmp((char *) uart_data, "yellow") == 0)
			{
				rgb_set_color(&MY_LED, rgb_yellow);
			}
        }
    }
}



void app_main(void)
{
	// Init LED
	rgb_init_LED(&MY_LED, 27, 12, 13);
	rgb_set_color(&MY_LED, rgb_black);

	xTaskCreate(echo_task, "uart_echo_task", 3072, NULL, 10, NULL);
	
    // Access point
    setup_softap();

    setup_csi();
    
    for(;;) {
		vTaskDelay(10);
    }

	// Station
	/* setup_station(); */

	/* setup_csi(); */
	
    /* for(;;) { */
    /* 	socket_transmitter_sta_loop(&is_wifi_connected); */
    /* } */
}

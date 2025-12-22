#include <stdio.h>
#include <sys/socket.h>
#include "rtc_wdt.h"
#include "driver/uart.h"

#include "EZADC.h"
#include "EZWIFI.h"
#include "rgb_led.h"

#define AP 1

#define SSID "CDIO"

#define CONFIG_WIFI_BANDWIDTH WIFI_BW_HT40
#define CONFIG_SEND_FREQUENCY 20
#define CONFIG_LESS_INTERFERENCE_CHANNEL 11

#define PORT                        3333
#define KEEPALIVE_IDLE              1
#define KEEPALIVE_INTERVAL          1
#define KEEPALIVE_COUNT             1

static const char *TAG = "CDIO CSI";

static const char *payload = "ESP";

static int port_iterate;

rgb_led MY_LED;

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

void battery_task (void *pvParameters)
{
	int battery_voltage;
	ADC MY_ADC;

	init_adc(&MY_ADC);

	config_adc(&MY_ADC, 7);
	
	while(1)
	{
		battery_voltage = ez_read(&MY_ADC);
		//ESP_LOGI(TAG, "Battery voltage: %d", battery_voltage);

		if(battery_voltage > 2000) {
			rgb_set_color(&MY_LED, rgb_green);
		}
		else if(battery_voltage > 1800) {
			rgb_set_color(&MY_LED, rgb_yellow);
		}
		else {
			rgb_set_color(&MY_LED, rgb_red);
		}
		
		vTaskDelay(pdMS_TO_TICKS(1000));
	}
}

static void do_retransmit(const int sock)
{
    int len;
    char rx_buffer[128];
	int8_t csi_buffer[256];
	wifi_csi_info_t *info;

    do {
        len = recv(sock, rx_buffer, sizeof(rx_buffer) - 1, 0);
        if (len < 0) {
            ESP_LOGE(TAG, "Error occurred during receiving: errno %d", errno);
        } else if (len == 0) {
            ESP_LOGW(TAG, "Connection closed");
        } else {
            rx_buffer[len] = 0; // Null-terminate whatever is received and treat it like a string
            ESP_LOGI(TAG, "Received %d bytes: %s", len, rx_buffer);

			if (strcmp(rx_buffer, "CSI") == 0)
			{			   
				info = get_csi();

				wifi_csi_info_t d = info[0];
				char mac[20] = {0};
				sprintf(mac,"%02X:%02X:%02X:%02X:%02X:%02X", d.mac[0], d.mac[1], d.mac[2], d.mac[3], d.mac[4], d.mac[5]);

				ets_printf("MAC: %s\nLength: %d\n", mac, info->len);

				send(sock, info->buf, sizeof(info->buf), 0);
			}
			//			else
			//			{
				// send() can return less bytes than supplied length.
				// Walk-around for robust implementation.
				int to_write = len;
				while (to_write > 0) {
					int written = send(sock, rx_buffer + (len - to_write), to_write, 0);
					if (written < 0) {
						ESP_LOGE(TAG, "Error occurred during sending: errno %d", errno);
						// Failed to retransmit, giving up
						return;
					}
					to_write -= written;
					//				}
            }
        }
    } while (len > 0);
}

static void tcp_server_task(void *pvParameters)
{
    char addr_str[128];
    int addr_family = (int)pvParameters;
    int ip_protocol = 0;
    int keepAlive = 1;
    int keepIdle = KEEPALIVE_IDLE;
    int keepInterval = KEEPALIVE_INTERVAL;
    int keepCount = KEEPALIVE_COUNT;
    struct sockaddr_storage dest_addr;

    if (addr_family == AF_INET) {
        struct sockaddr_in *dest_addr_ip4 = (struct sockaddr_in *)&dest_addr;
        dest_addr_ip4->sin_addr.s_addr = htonl(INADDR_ANY);
        dest_addr_ip4->sin_family = AF_INET;
        dest_addr_ip4->sin_port = htons(PORT + port_iterate);
        ip_protocol = IPPROTO_IP;
    }

    int listen_sock = socket(addr_family, SOCK_STREAM, ip_protocol);
    if (listen_sock < 0) {
        ESP_LOGE(TAG, "Unable to create socket: errno %d", errno);
        vTaskDelete(NULL);
        return;
    }
    int opt = 1;
    setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    ESP_LOGI(TAG, "Socket created");

    int err = bind(listen_sock, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
    if (err != 0) {
        ESP_LOGE(TAG, "Socket unable to bind: errno %d", errno);
        ESP_LOGE(TAG, "IPPROTO: %d", addr_family);
        goto CLEAN_UP;
    }
    ESP_LOGI(TAG, "Socket bound, port %d", PORT);

    err = listen(listen_sock, 1);
    if (err != 0) {
        ESP_LOGE(TAG, "Error occurred during listen: errno %d", errno);
        goto CLEAN_UP;
    }

    while (1) {

        ESP_LOGI(TAG, "Socket listening");

        struct sockaddr_storage source_addr; // Large enough for both IPv4 or IPv6
        socklen_t addr_len = sizeof(source_addr);
        int sock = accept(listen_sock, (struct sockaddr *)&source_addr, &addr_len);
        if (sock < 0) {
            ESP_LOGE(TAG, "Unable to accept connection: errno %d", errno);
            break;
        }

        // Set tcp keepalive option
        setsockopt(sock, SOL_SOCKET, SO_KEEPALIVE, &keepAlive, sizeof(int));
        setsockopt(sock, IPPROTO_TCP, TCP_KEEPIDLE, &keepIdle, sizeof(int));
        setsockopt(sock, IPPROTO_TCP, TCP_KEEPINTVL, &keepInterval, sizeof(int));
        setsockopt(sock, IPPROTO_TCP, TCP_KEEPCNT, &keepCount, sizeof(int));
        // Convert ip address to string
        if (source_addr.ss_family == PF_INET) {
            inet_ntoa_r(((struct sockaddr_in *)&source_addr)->sin_addr, addr_str, sizeof(addr_str) - 1);
        }

        ESP_LOGI(TAG, "Socket accepted ip address: %s", addr_str);

        do_retransmit(sock);

        shutdown(sock, 0);
        close(sock);
    }

CLEAN_UP:
    close(listen_sock);
    vTaskDelete(NULL);
}

void tcp_client_task(void *pvParameters)
{
	char rx_buffer[128];	
	char host_ip[] = "192.168.4.1";	
	int addr_family = 0;
	int ip_protocol = 0;

	while(1)
	{
		struct sockaddr_in dest_addr;
		inet_pton(AF_INET, host_ip, &dest_addr.sin_addr);
        dest_addr.sin_family = AF_INET;
        dest_addr.sin_port = htons(PORT);
        addr_family = AF_INET;
        ip_protocol = IPPROTO_IP;

		int connected = 0;
		while(!connected)
		{
			connected = is_wifi_connected();
			vTaskDelay(pdTICKS_TO_MS(1000));
		}

		int sock =  socket(addr_family, SOCK_STREAM, ip_protocol);
        if (sock < 0) {
            ESP_LOGE(TAG, "Unable to create socket: errno %d", errno);
            break;
        }
        ESP_LOGI(TAG, "Socket created, connecting to %s:%d", host_ip, PORT);

        int err = connect(sock, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
        if (err != 0) {
            ESP_LOGE(TAG, "Socket unable to connect: errno %d", errno);
            break;
        }
        ESP_LOGI(TAG, "Successfully connected");

        while (1) {
            int err = send(sock, payload, strlen(payload), 0);
            if (err < 0) {
                ESP_LOGE(TAG, "Error occurred during sending: errno %d", errno);
                break;
            }

            int len = recv(sock, rx_buffer, sizeof(rx_buffer) - 1, 0);
            // Error occurred during receiving
            if (len < 0) {
                ESP_LOGE(TAG, "recv failed: errno %d", errno);
                break;
            }
            // Data received
            else {
                rx_buffer[len] = 0; // Null-terminate whatever we received and treat like a string
                ESP_LOGI(TAG, "Received %d bytes from %s:", len, host_ip);
                ESP_LOGI(TAG, "%s", rx_buffer);
            }
			vTaskDelay(pdTICKS_TO_MS(100));
        }

        if (sock != -1) {
            ESP_LOGE(TAG, "Shutting down socket and restarting...");
            shutdown(sock, 0);
            close(sock);
        }
	}
}

void app_main(void)
{	
	// Init LED
	rgb_init_LED(&MY_LED, 27, 12, 13);
	rgb_set_color(&MY_LED, rgb_black);

	xTaskCreate(echo_task, "uart_echo", 3072, NULL, 10, NULL);

	xTaskCreate(battery_task, "battery", 2048, NULL, 1, NULL);
	
#if AP
	setup_softap();

    setup_csi("F8:B3:B7:5A:34:F4");

	for (int i = 0;i < 2;i++)
	{
		port_iterate = i;
		xTaskCreate(tcp_server_task, "tcp_server", 4096, (void*)AF_INET, 5, NULL);
		vTaskDelay(pdTICKS_TO_MS(100));
	}
#else
	setup_station();

	// setup_csi("F0:24:F9:54:3B:89");

	xTaskCreate(tcp_client_task, "tcp_client", 4096, (void*)AF_INET, 5, NULL);
#endif
}

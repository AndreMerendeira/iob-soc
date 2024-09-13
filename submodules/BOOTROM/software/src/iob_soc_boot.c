#include "bsp.h"
#include "iob_soc_conf.h"
#include "iob_soc_periphs.h"
#include "iob_soc_system.h"
#include "iob_uart.h"

#define PROGNAME "IOb-Bootloader"

int main() {

  // init uart
  uart_init(UART0_BASE, FREQ / BAUD);

  // connect with console
  do {
    if (IOB_UART_GET_TXREADY())
      uart_putc((char)ENQ);
  } while (!IOB_UART_GET_RXREADY());

  // welcome message
  uart_puts(PROGNAME);
  uart_puts(": connected!\n");

#ifdef IOB_SOC_USE_EXTMEM
  uart_puts(PROGNAME);
  uart_puts(": DDR in use and program runs from DDR\n");
#endif

  // address to copy firmware to
  char *prog_start_addr = (char *)IOB_SOC_FW_ADDR;

  while (uart_getc() != ACK) {
    uart_puts(PROGNAME);
    uart_puts(": Waiting for Console ACK.\n");
  }

#ifndef IOB_SOC_INIT_MEM
  // receive firmware from host
  int file_size = 0;
  char r_fw[] = "iob_soc_firmware.bin";
  file_size = uart_recvfile(r_fw, prog_start_addr);
  uart_puts(PROGNAME);
  uart_puts(": Loading firmware...\n");

  // sending firmware back for debug
  char s_fw[] = "s_fw.bin";

  if (file_size)
    uart_sendfile(s_fw, file_size, prog_start_addr);
  else {
    uart_puts(PROGNAME);
    uart_puts(": ERROR loading firmware\n");
  }
#endif

  // run firmware
  uart_puts(PROGNAME);
  uart_puts(": Restart CPU to run user program...\n");
  uart_txwait();
}
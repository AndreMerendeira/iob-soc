#include "stdlib.h"
#include <stdio.h>
#include "system.h"
#include "periphs.h"
#include "iob-uart.h"
#include "printf.h"
#include "iob-regfileif.h"

int main()
{
  //init uart
  uart_init(UART0_BASE,FREQ/BAUD);   
  uart_puts("\n\n\nHello world!\n\n\n");

  //run REGFILEIF tests if the system was built with it (and the Tester)
  regfileif_setbaseaddr(REGFILEIF0_BASE);

  //Write to UART0 connected to the Tester.
  uart_puts("This message was sent from SUT!\n");

  //Write data to the registers of REGFILEIF to be read by the Tester.
  regfileif_writereg(2, 128);
  regfileif_writereg(3, 1024);

#ifdef USE_DDR
#ifdef RUN_EXTMEM
  char sutMemoryMessage[]="This message is stored in SUT's memory\n";
  
  //Give address of stored message to Tester using regfileif register 4
  regfileif_writereg(4, (int)sutMemoryMessage);
#else
  char ddrMemoryMessage[]="This message was written to DDR by the SUT\n", *strPtr;
  int i;
  //Write string to DDR, starting at address 0, to later be read by tester
  strPtr=(char*)(0b1 << E); //Address 0 of DDR
  for(i=0; ddrMemoryMessage[i]!='\0'; i++){
    strPtr[i]=ddrMemoryMessage[i];
  }
#endif
#endif

  uart_finish();
}

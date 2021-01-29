//add core test module in testbench

    wire uart_interr;
	//assign irq[3:0]=0;
	//assign irq[4]=uart_interr;
	//assign irq[31:5]=0;
   	
   	
   iob_uart uart_0_tb
     (
      .clk       (clk),
      .rst       (reset),

      .valid     (uart_valid),
      .address   (uart_addr),
      .wdata     (uart_wdata[`UART0_WDATA_W-1:0]),
      .wstrb     (uart_wstrb),
      .rdata     (uart_rdata),
      .ready     (uart_ready),

      .txd       (uart_rxd),
      .rxd       (uart_txd),
      .rts       (uart_cts),
      .cts       (uart_rts),
      
      .interrupt (uart_interr)
      );

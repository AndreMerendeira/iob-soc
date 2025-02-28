`timescale 1ns / 1ps

module iob_modcnt #(
   parameter DATA_W  = 21,
   parameter RST_VAL = {DATA_W{1'b0}}
) (

   `include "clk_en_rst_s_port.vs"

   input rst_i,
   input en_i,

   input  [DATA_W-1:0] mod_i,
   output [DATA_W-1:0] data_o
);

   wire ld_count;
   assign ld_count = (data_o >= mod_i);

   wire [DATA_W-1:0] data;
   assign data = ld_count ? {DATA_W{1'b0}} : data_o + 1'b1;

   iob_reg_re #(
      .DATA_W (DATA_W),
      .RST_VAL(RST_VAL)
   ) reg0 (
      `include "clk_en_rst_s_s_portmap.vs"
      .rst_i (rst_i),
      .en_i  (en_i),
      .data_i(data),
      .data_o(data_o)
   );

endmodule

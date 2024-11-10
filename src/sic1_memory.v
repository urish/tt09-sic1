/*
 * Copyright (c) 2024 Uri Shaked
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module sic1_memory (
    input wire clk,
    input wire rst_n,
    input wire [7:0] addr,
    input wire wr_en,
    input wire [7:0] data_in,
    output wire [7:0] data_out,
    input wire [7:0] ui_in,
    output reg [7:0] uo_out,
    output reg out_strobe
);
  parameter ADDR_MAX = 8'd252;
  parameter ADDR_IN = 8'd253;
  parameter ADDR_OUT = 8'd254;

  reg [7:0] mem[ADDR_MAX:0];

  wire is_ram_addr = addr <= ADDR_MAX;

  assign data_out = is_ram_addr ? mem[addr] : addr === ADDR_IN ? ui_in : 8'h00;

  always @(posedge clk) begin
    if (~rst_n) begin
      uo_out <= 8'h00;
      out_strobe <= 1'b0;
    end else if (wr_en) begin
      out_strobe <= 1'b0;
      if (is_ram_addr) begin
        mem[addr] <= data_in;
      end else if (addr == ADDR_OUT) begin
        uo_out <= data_in;
        out_strobe <= 1'b1;
      end
    end
  end

endmodule

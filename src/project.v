/*
 * Copyright (c) 2024 Uri Shaked
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_urish_sic1 (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  localparam STATE_HALT = 3'd0;
  localparam STATE_READ_A = 3'd1;
  localparam STATE_READ_B = 3'd2;
  localparam STATE_READ_C = 3'd3;
  localparam STATE_READ_MEM_A = 3'd4;
  localparam STATE_READ_MEM_B = 3'd5;
  localparam STATE_STORE_RESULT = 3'd6;

  reg [2:0] state;
  reg [7:0] PC;
  reg [7:0] mem_addr;
  reg mem_wr_en;
  reg [7:0] mem_data_in;
  wire [7:0] mem_data_out;
  reg prev_run;

  reg [7:0] A;
  reg [7:0] B;
  reg [7:0] C;
  reg [7:0] mem_A;
  wire [7:0] next_PC = (mem_data_in == 0 || mem_data_in[7]) ? C : PC + 3;

  wire halted = state == STATE_HALT;
  wire out_strobe;
  assign uio_out = {3'b0, out_strobe, 2'b0, halted, 1'b0};
  assign uio_oe  = 8'b00010010;

  // Debug stuff
  reg [63:0] state_name;
  always @(*) begin
    case (state)
      STATE_HALT: state_name = "Halt";
      STATE_READ_A: state_name = "ReadA";
      STATE_READ_B: state_name = "ReadB";
      STATE_READ_C: state_name = "ReadC";
      STATE_READ_MEM_A: state_name = "ReadMemA";
      STATE_READ_MEM_B: state_name = "ReadMemB";
      STATE_STORE_RESULT: state_name = "StoreRes";
      default: state_name = "Invalid";
    endcase
  end

  sic1_memory mem (
      .clk(clk),
      .rst_n(rst_n),
      .addr(mem_addr),
      .wr_en(mem_wr_en),
      .data_in(mem_data_in),
      .data_out(mem_data_out),
      .ui_in(ui_in),
      .uo_out(uo_out),
      .out_strobe(out_strobe)
  );

  wire run = uio_in[0];
  wire set_pc = uio_in[2];
  wire set_data = uio_in[3];

  always @(posedge clk) begin
    if (~rst_n) begin
      state <= STATE_HALT;
      PC <= 8'h00;
      mem_addr <= 8'h00;
      mem_wr_en <= 1'b0;
      mem_data_in <= 8'h00;
      A <= 8'h00;
      B <= 8'h00;
      C <= 8'h00;
      mem_A <= 8'h00;
      prev_run <= 1'b0;
    end else begin
      mem_wr_en <= 1'b0;
      prev_run  <= run;

      case (state)
        STATE_HALT: begin
          if (set_data) begin
            mem_wr_en   <= 1'b1;
            mem_addr    <= PC;
            mem_data_in <= ui_in;
            PC          <= PC + 1;
          end
          if (set_pc) begin
            PC <= ui_in;
          end
          if (run && !prev_run && PC <= 8'd252) begin
            mem_addr <= PC;
            state <= STATE_READ_A;
          end
        end
        STATE_READ_A: begin
          A <= mem_data_out;
          mem_addr <= mem_addr + 1;
          state <= STATE_READ_B;
        end
        STATE_READ_B: begin
          B <= mem_data_out;
          mem_addr <= mem_addr + 1;
          state <= STATE_READ_C;
        end
        STATE_READ_C: begin
          C <= mem_data_out;
          mem_addr <= A;
          state <= STATE_READ_MEM_A;
        end
        STATE_READ_MEM_A: begin
          mem_A <= mem_data_out;
          mem_addr <= B;
          state <= STATE_READ_MEM_B;
        end
        STATE_READ_MEM_B: begin
          mem_data_in <= mem_A - mem_data_out;
          mem_addr <= A;
          mem_wr_en <= 1'b1;
          state <= STATE_STORE_RESULT;
        end
        STATE_STORE_RESULT: begin
          PC <= next_PC;
          mem_addr <= next_PC;
          state <= run && next_PC <= 252 ? STATE_READ_A : STATE_HALT;
        end
        default: state <= STATE_HALT;
      endcase
    end
  end

  // // List all unused inputs to prevent warnings
  wire _unused = &{ena, 1'b0};

endmodule

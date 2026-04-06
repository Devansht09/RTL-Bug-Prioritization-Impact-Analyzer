module spi_master (
    input clk,
    input rst_n,
    input start,
    input [7:0] tx_data,
    output reg mosi,
    output sck,
    output reg cs_n
);
    reg [2:0] state;
    reg clk_div;
    
    assign sck = clk_div;
    
    always @(state) begin // LATCH RISK
        if (state == 1) cs_n = 0;
        else if (state == 0) cs_n = 1;
        // missing default assignment
    end
endmodule

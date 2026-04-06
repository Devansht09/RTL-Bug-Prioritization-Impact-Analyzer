module async_fifo (
    input clk_write,
    input clk_read,
    input rst,
    input [7:0] din,
    input write_en,
    input read_en,
    output reg [7:0] dout,
    output full,
    output empty
);
    reg [7:0] mem [0:15];
    reg [3:0] wptr;
    reg [3:0] rptr;
    wire unused_flag; // Unused
    
    assign full = (wptr == rptr + 15);
    assign empty = (wptr == rptr);
    
    always @(posedge clk_write or posedge rst) begin
        if (rst) wptr <= 0;
        else if (write_en && !full) begin
            mem[wptr] <= din;
            wptr <= wptr + 1;
        end
    end
    
    always @(posedge clk_read or posedge rst) begin
        if (rst) rptr <= 0;
        else if (read_en && !empty) begin
            dout <= mem[rptr];
            rptr <= rptr + 1;
        end
    end
endmodule

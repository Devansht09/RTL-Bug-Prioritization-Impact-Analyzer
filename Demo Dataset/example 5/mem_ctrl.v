module mem_ctrl (
    input clk,
    input req,
    output reg ack,
    output reg [31:0] addr
);
    wire [7:0] dead_signal; // unused
    
    always @(posedge clk) begin
        if (req) begin
            ack <= 1;
        end else begin
            ack <= 0;
        end
    end
endmodule

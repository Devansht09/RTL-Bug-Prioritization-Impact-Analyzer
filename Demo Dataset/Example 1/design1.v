module design1(input a, input b, input clk, output reg y);

wire temp1;
wire temp2;
wire unused_signal;

assign temp1 = a & b;
assign temp2 = temp1;

// Conflicting assignment (HIGH)
assign y = temp2;
assign y = a | b;

// Latch risk (MEDIUM)
always @(*) begin
    if (a)
        temp2 = b;
end

endmodule
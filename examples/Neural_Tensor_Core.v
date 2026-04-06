module design_big1(input a, input b, input c, input clk, output reg y);

wire n1, n2, n3, n4, n5;
wire unused1, unused2;
reg state;

// Deep propagation chain
assign n1 = a & b;
assign n2 = n1 | c;
assign n3 = n2 ^ b;
assign n4 = n3 & a;
assign n5 = n4 | c;

// HIGH: conflicting output assignment
assign y = n5;
assign y = a ^ b;

// HIGH: control path latch risk
always @(*) begin
    if (a)
        state = b;
end

// MEDIUM: conflicting internal signal
assign n2 = a & c;

// LOW: unused junk
wire garbage1;
wire garbage2;

endmodule
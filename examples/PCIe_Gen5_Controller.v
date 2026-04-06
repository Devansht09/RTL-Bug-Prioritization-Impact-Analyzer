module design_mega(
    input clk,
    input reset,
    input a, b, c, d,
    output reg y
);

// ===== Signals =====
wire n1, n2, n3, n4, n5, n6, n7, n8, n9, n10;
wire n11, n12, n13, n14, n15;
wire unused1, unused2, unused3;
wire undriven1;
reg state1, state2, state3;

// ===== Deep Data Path =====
assign n1 = a & b;
assign n2 = n1 | c;
assign n3 = n2 ^ d;
assign n4 = n3 & a;
assign n5 = n4 | b;
assign n6 = n5 ^ c;
assign n7 = n6 & d;
assign n8 = n7 | a;
assign n9 = n8 ^ b;
assign n10 = n9 & c;

// HIGH: upstream corruption
assign n1 = c | d;

// ===== More propagation =====
assign n11 = n10 | n2;
assign n12 = n11 ^ n3;
assign n13 = n12 & n4;
assign n14 = n13 | n5;
assign n15 = n14 ^ n6;

// ===== Output corruption (HIGH) =====
assign y = n15;
assign y = a ^ b;

// ===== Control logic (VERY BAD) =====

// HIGH: latch risk
always @(*) begin
    if (reset)
        state1 = 0;
end

// HIGH: another latch
always @(*) begin
    if (a)
        state2 = b;
end

// MEDIUM: incomplete condition
always @(*) begin
    if (c)
        state3 = d;
end

// ===== Sequential logic =====
always @(posedge clk) begin
    y <= n15;
end

// ===== Internal conflicts =====

// MEDIUM: conflicting assignment mid chain
assign n4 = b & c;

// MEDIUM: multiple drivers
assign n8 = a & d;

// ===== Undriven =====
wire floating_signal;

// ===== Garbage =====
wire junk1, junk2, junk3;

// ===== Extra broken logic =====

// HIGH: affects control → output
assign state1 = n10;

// HIGH: feedback loop
assign n3 = n15;

// MEDIUM: redundant overwrite
assign n6 = a & b;

endmodule
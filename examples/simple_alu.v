// simple_alu.v
// Intentionally buggy ALU module for RTL Bug Analyzer testing
// Contains: unused signals, undriven signals, conflicting assignments, latch risk

module simple_alu (
    input  wire        clk,
    input  wire        rst,
    input  wire [7:0]  a,
    input  wire [7:0]  b,
    input  wire [1:0]  op,
    output reg  [7:0]  result,
    output wire        carry_out,
    output wire        zero_flag
);

    // BUG 1: unused_signal -- declared but never used anywhere
    wire [7:0] unused_signal;

    // BUG 2: undriven_wire -- declared but never assigned
    wire [7:0] undriven_wire;

    // Intermediate signals
    wire [7:0] and_result;
    wire [7:0] or_result;
    wire [8:0] add_result;
    wire [7:0] xor_result;

    // dependency chain: a,b → and_result → result
    assign and_result = a & b;

    // dependency chain: a,b → or_result → result
    assign or_result = a | b;

    // dependency chain: a,b → add_result → result + carry_out
    assign add_result = {1'b0, a} + {1'b0, b};

    // dependency chain: a,b → xor_result → result
    assign xor_result = a ^ b;

    // carry_out depends on add_result
    assign carry_out = add_result[8];

    // zero_flag depends on result
    assign zero_flag = (result == 8'b0);

    // BUG 3: Conflicting assignment — result driven from both always block AND wire below
    wire [7:0] forced_result;
    assign forced_result = 8'hFF; // This conflicts with the always block below

    // BUG 4: Latch risk — 'op' not fully covered (no default), result may latch
    always @(*) begin
        case (op)
            2'b00: result = and_result;
            2'b01: result = or_result;
            2'b10: result = add_result[7:0];
            // MISSING 2'b11 case — latch risk for xor_result
            // result not assigned for op=2'b11
        endcase
    end

    // BUG 5: Conflicting assignment — result is reg driven above, also attempted here
    // (In synthesized logic, this would cause a conflict)
    // wire attempt_conflict = result; // commented but pattern detected by parser

endmodule


// Secondary module to test cross-module dependency tracking
module alu_wrapper (
    input  wire        sys_clk,
    input  wire [7:0]  data_a,
    input  wire [7:0]  data_b,
    input  wire [1:0]  operation,
    output wire [7:0]  alu_out,
    output wire        overflow
);

    // BUG 6: unused input port (operation never connected inside this module properly)
    wire [7:0] internal_result;
    wire       internal_carry;

    // BUG 7: undriven signal in wrapper
    wire [3:0] debug_bus;

    simple_alu alu_inst (
        .clk(sys_clk),
        .rst(1'b0),
        .a(data_a),
        .b(data_b),
        .op(operation),
        .result(internal_result),
        .carry_out(internal_carry),
        .zero_flag()
    );

    assign alu_out  = internal_result;
    assign overflow = internal_carry;

endmodule

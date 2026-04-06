module alu_pipeline (
    input clk,
    input [31:0] a, b,
    input [3:0] op,
    output reg [31:0] out
);
    wire [15:0] internal_wire; // Undriven
    reg [31:0] stage1_a, stage1_b;
    
    always @(posedge clk) begin
        stage1_a <= a;
        stage1_b <= b;
    end
    
    always @(posedge clk) begin
        out <= stage1_a + stage1_b + internal_wire;
    end
endmodule

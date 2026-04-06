module clk_div (
    input clk_in,
    input preset,
    output reg clk_out,
    output clk_out_inv
);
    assign clk_out_inv = ~clk_out;
    
    always @(posedge clk_in) begin
        if (preset) clk_out <= 1; // Conflicting if another block assigns
    end
    
    always @(posedge clk_in) begin
        if (!preset) clk_out <= ~clk_out; // Conflict
    end
endmodule

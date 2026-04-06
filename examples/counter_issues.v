// counter_issues.v
// Buggy synchronous counter with pipeline stage
// Contains: latch risk, undriven signals, conflicting assigns, unused wires

module sync_counter (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    input  wire        load,
    input  wire [7:0]  load_val,
    output reg  [7:0]  count,
    output wire        count_done,
    output wire        overflow,
    output reg         parity_out
);

    // dependency: count → count_done
    assign count_done = (count == 8'hFF);

    // BUG 1: drive chain broken — overflow is declared as output but never driven
    // assign overflow = ???;   <-- missing assignment

    // BUG 2: Unused internal register
    reg [7:0] shadow_count;

    // BUG 3: Undriven wire
    wire [7:0] next_count_debug;

    // dependency: load_val → count (via load path)
    // dependency: count → count (self-loop on increment)

    // BUG 4: Latch risk — 'load' condition handled but 'enable' branch has no else
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 8'b0;
        end else if (load) begin
            count <= load_val;
        end else if (enable) begin
            count <= count + 1;
        end
        // No else — if enable=0 and load=0 and rst_n=1 → count retains (implicit latch in combo logic)
    end

    // BUG 5: Conflicting parity logic — parity_out assigned in two always blocks
    always @(*) begin
        parity_out = ^count;  // XOR reduction for parity
    end

    // Second always block also drives parity_out — conflict!
    always @(posedge clk) begin
        if (count[0])
            parity_out <= 1'b1;
        // BUG 6: Missing else — parity_out not assigned when count[0]=0 → latch
    end

endmodule


// Pipeline stage module
module counter_pipeline (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  stage_in,
    output reg  [7:0]  stage_out,
    output wire        valid_out
);

    // BUG 7: valid_out never driven (undriven output)
    // assign valid_out = ???;

    // BUG 8: Unused wire
    wire [7:0] bypass_wire;

    // dependency: stage_in → stage_out
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            stage_out <= 8'b0;
        else
            stage_out <= stage_in;
    end

endmodule

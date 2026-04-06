import os
import json

base_dir = "Demo Dataset"
os.makedirs(base_dir, exist_ok=True)

# Example 1: FIFO (Contains an unused flag + external sync reset warning)
dir1 = os.path.join(base_dir, "example 1")
os.makedirs(dir1, exist_ok=True)
with open(os.path.join(dir1, "async_fifo.v"), "w") as f:
    f.write('''module async_fifo (
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
''')
with open(os.path.join(dir1, "detected_issues.json"), "w") as f:
    json.dump([
        {"type": "external", "signal": "rst", "module": "async_fifo", "confidence": 0.95, "description": "Reset domain crossing without synchronization"}
    ], f, indent=2)


# Example 2: SPI Master (Contains a Latch Risk state machine)
dir2 = os.path.join(base_dir, "example 2")
os.makedirs(dir2, exist_ok=True)
with open(os.path.join(dir2, "spi_master.v"), "w") as f:
    f.write('''module spi_master (
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
''')
with open(os.path.join(dir2, "detected_issues.json"), "w") as f:
    json.dump([
        {"type": "external", "signal": "state", "module": "spi_master", "confidence": 0.88, "description": "State machine encoding uses non-optimal binary format for FSM"}
    ], f, indent=2)


# Example 3: Pipeline (Contains an Undriven internal wire affecting the output)
dir3 = os.path.join(base_dir, "example 3")
os.makedirs(dir3, exist_ok=True)
with open(os.path.join(dir3, "alu_pipeline.v"), "w") as f:
    f.write('''module alu_pipeline (
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
''')
with open(os.path.join(dir3, "detected_issues.json"), "w") as f:
    json.dump([
        {"type": "external", "signal": "out", "module": "alu_pipeline", "confidence": 0.92, "description": "Pipeline stage missing backpressure control causing potential data loss"}
    ], f, indent=2)


# Example 4: Clock Divider (Contains a Conflicting Assignment logic fail)
dir4 = os.path.join(base_dir, "example 4")
os.makedirs(dir4, exist_ok=True)
with open(os.path.join(dir4, "clk_div.v"), "w") as f:
    f.write('''module clk_div (
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
''')
with open(os.path.join(dir4, "detected_issues.json"), "w") as f:
    json.dump([
        {"type": "external", "signal": "clk_in", "module": "clk_div", "confidence": 1.0, "description": "Clock signal driving data inputs directly"}
    ], f, indent=2)


# Example 5: Memory Controller (Clean but has an External JSON warnings)
dir5 = os.path.join(base_dir, "example 5")
os.makedirs(dir5, exist_ok=True)
with open(os.path.join(dir5, "mem_ctrl.v"), "w") as f:
    f.write('''module mem_ctrl (
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
''')
with open(os.path.join(dir5, "detected_issues.json"), "w") as f:
    json.dump([
        {"type": "external", "signal": "dead_signal", "module": "mem_ctrl", "confidence": 0.8, "description": "Suspicious prefix 'dead_' suggests deprecated logic"},
        {"type": "external", "signal": "req", "module": "mem_ctrl", "confidence": 0.75, "description": "High fanout on req signal potentially missing timing"}
    ], f, indent=2)

print("Demo Dataset created and populated successfully.")

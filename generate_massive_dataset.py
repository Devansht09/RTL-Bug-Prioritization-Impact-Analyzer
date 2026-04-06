import os
import shutil
import json

base_dir = "Demo Dataset"
os.makedirs(base_dir, exist_ok=True)

# -------------------------------------------------------------------------
# EXAMPLE 2: NEURAL TENSOR CORE (Massive pipeline, massive fanout)
# -------------------------------------------------------------------------
dir_ex2 = os.path.join(base_dir, "example 2")
os.makedirs(dir_ex2, exist_ok=True)

v_ex2 = """module Neural_Tensor_Core (
    input clk,
    input rst_n,
    input [255:0] activation_in,
    input [255:0] weight_in,
    output reg [255:0] mac_out,
    output reg ready_flag,
    output wire fatal_error
);
    // Huge fanout clock gate (Timing risk = 1, fanout = High -> HIGH priority bug)
    reg tensor_clk_en;
    
    // CONFLICTING ASSIGNMENT (Bug #1: HIGH)
    always @(posedge clk) begin
        tensor_clk_en <= 1'b1;
    end
    always @(negedge clk) begin
        tensor_clk_en <= 1'b0;
    end

    // UNDRIVEN SIGNAL massive fanout (Bug #2: HIGH)
    wire [15:0] critical_bias_vector; 
    
    // Massive pipeline generation
"""
for i in range(50):
    v_ex2 += f"    reg [255:0] pipe_stage_{i};\n"
    
for i in range(25):
    v_ex2 += f"    wire [7:0] unused_debug_node_{i};\n"
    v_ex2 += f"    assign unused_debug_node_{i} = activation_in[{i}];\n" # Unused bugs (LOW)

v_ex2 += """
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
"""
for i in range(50):
    v_ex2 += f"            pipe_stage_{i} <= 0;\n"
v_ex2 += """        end else if (tensor_clk_en) begin
            pipe_stage_0 <= activation_in ^ weight_in ^ {16{critical_bias_vector}};
"""
for i in range(1, 50):
    v_ex2 += f"            pipe_stage_{i} <= pipe_stage_{i-1};\n"
v_ex2 += """        end
    end

    // UNDRIVEN SIGNAL propagating to output (Bug #3-8: MEDIUM)
    wire [255:0] undriven_bias_1;
    wire [255:0] undriven_bias_2;
    wire [255:0] undriven_bias_3;
    wire [255:0] undriven_bias_4;
    wire [255:0] undriven_bias_5;
    wire [255:0] undriven_bias_6;

    always @(posedge clk) begin
        mac_out <= pipe_stage_49 ^ undriven_bias_1 ^ undriven_bias_2 ^ undriven_bias_3 ^ undriven_bias_4 ^ undriven_bias_5 ^ undriven_bias_6;
        ready_flag <= 1'b1;
    end
    
    // LATCH RISK directly on output (Bug #9: HIGH)
    always @(*) begin
        if (mac_out[0]) fatal_error = 1'b1;
    end
endmodule
"""

with open(os.path.join(dir_ex2, "Neural_Tensor_Core.v"), "w") as f:
    f.write(v_ex2)

ex2_issues = [
    {
        "type": "clock_domain_crossing",
        "signal": "ready_flag",
        "module": "Neural_Tensor_Core",
        "confidence": 1.0,
        "description": "High risk CDC failure on output ready flag."
    },
    {
        "type": "setup_time_violation",
        "signal": "mac_out",
        "module": "Neural_Tensor_Core",
        "confidence": 0.98,
        "description": "Severe timing closure failure (setup) due to 50-stage deep combination logic sink."
    }
]
with open(os.path.join(dir_ex2, "detected_issues.json"), "w") as f:
    json.dump(ex2_issues, f, indent=2)

# -------------------------------------------------------------------------
# EXAMPLE 3: PCIE GEN5 CONTROLLER (Huge FSM, wide buses)
# -------------------------------------------------------------------------
dir_ex3 = os.path.join(base_dir, "example 3")
os.makedirs(dir_ex3, exist_ok=True)

v_ex3 = """module PCIe_Gen5_Controller (
    input pcie_clk,
    input sys_rst,
    input [127:0] rx_axis_data,
    output reg [127:0] tx_axis_data,
    output reg link_up_status,
    output wire pcie_error_intr
);
    // UNDRIVEN SIGNAL with Clock name to boost timing score (Bug #1: HIGH)
    wire [3:0] ref_clock_sync_loss;
    
    // CONFLICTING ASSIGNMENT on critical output (Bug #2: HIGH)
    always @(posedge pcie_clk) begin
        link_up_status <= 1'b1;
    end
    always @(negedge pcie_clk) begin
        link_up_status <= ~sys_rst;
    end

    // State machine generation
    reg [255:0] fsm_state;
    reg [127:0] data_buffer [0:63];
"""
v_ex3 += "    // UNDRIVEN SIGNALS propagating to output (Bug #3-9: MEDIUM)\n"
for i in range(7):
    v_ex3 += f"    wire [127:0] routing_layer_undriven_{i};\n"

v_ex3 += "    // UNUSED SIGNALS (Bug #10-30: LOW)\n"
for i in range(20):
    v_ex3 += f"    wire [3:0] unused_lane_config_{i};\n"
    v_ex3 += f"    assign unused_lane_config_{i} = rx_axis_data[{i*4}+3:{i*4}];\n"

v_ex3 += """
    always @(posedge pcie_clk or posedge sys_rst) begin
        if (sys_rst) begin
            fsm_state <= 0;
            tx_axis_data <= 0;
        end else begin
            case (fsm_state[3:0] ^ ref_clock_sync_loss)
"""
for i in range(16):
    modifiers = " ^ ".join([f"routing_layer_undriven_{x}" for x in range(7)])
    v_ex3 += f"                4'd{i}: tx_axis_data <= rx_axis_data ^ {modifiers};\n"
    
v_ex3 += """
                default: tx_axis_data <= rx_axis_data;
            endcase
            fsm_state <= {fsm_state[254:0], 1'b1};
        end
    end
    
    // LATCH RISK (Bug #31: HIGH)
    always @(*) begin
        if (rx_axis_data == 0) pcie_error_intr = 1'b1;
        // missing default assignment
    end
endmodule
"""

with open(os.path.join(dir_ex3, "PCIe_Gen5_Controller.v"), "w") as f:
    f.write(v_ex3)

ex3_issues = [
    {
        "type": "latch_risk",
        "signal": "tx_axis_data",
        "module": "PCIe_Gen5_Controller",
        "confidence": 0.95,
        "description": "FSM missing state coverage leading to implicit memory."
    },
    {
        "type": "floating_output",
        "signal": "pcie_error_intr",
        "module": "PCIe_Gen5_Controller",
        "confidence": 0.99,
        "description": "Critical interrupt output might float in certain PCIe physical layer states."
    },
    {
        "type": "meta_stability",
        "signal": "fsm_state",
        "module": "PCIe_Gen5_Controller",
        "confidence": 0.85,
        "description": "State vector meta-stability warning."
    }
]
with open(os.path.join(dir_ex3, "detected_issues.json"), "w") as f:
    json.dump(ex3_issues, f, indent=2)

print("Generated massive datasets for Example 2 and 3 successfully!")

import os
import shutil
import json

base_dir = "Demo Dataset"
if os.path.exists(base_dir):
    shutil.rmtree(base_dir, ignore_errors=True)
os.makedirs(base_dir, exist_ok=True)

modules = [
    # (name, folder, high_wanted, med_wanted, low_wanted)
    ("ALU_SuperScalar", "example 1", 4, 6, 13),
    ("Neural_Tensor_Core", "example 2", 3, 8, 12),
    ("Crypto_Engine_AES", "example 3", 5, 4, 11)
]

for mod_name, folder_name, n_high, n_med, n_low in modules:
    dir_path = os.path.join(base_dir, folder_name)
    os.makedirs(dir_path, exist_ok=True)
    
    # Base module yields exactly 3 High inherently (Latch, Conflict, Undriven Output port)
    # Remaining high bugs are injected via external JSON on an output port.
    json_highs = n_high - 3
    
    # Base JSON yields exactly 1 Low (Naming convention)
    # Remaining low bugs are injected via unused wires in Verilog.
    unused_amount = n_low - 1
    
    v_code = f"""module {mod_name} (
    input clk,
    input rst,
    input [31:0] stream_in,
    output reg [31:0] stream_out,
    output reg error_flag,
    output reg valid_flag,
    output wire debug_sync
);
    // -----------------------------------------------------
    // HIGH PRIORITY BUGS ({n_high} total requested)
    // -----------------------------------------------------
    // 1. Latch Risk intentionally directly on the output reg
    always @(*) begin
        if (stream_in == 0) stream_out = 32'h0;
    end

    // 2. Conflicting Assignment directly on the output reg
    always @(posedge clk) begin
        error_flag <= 1'b1;
    end
    always @(negedge clk) begin
        error_flag <= 1'b0; 
    end
    
    // 3. Undriven Output Port (debug_sync)
    // Extras ({json_highs}) are provided via detected_issues.json
    
    // -----------------------------------------------------
    // MEDIUM PRIORITY BUGS ({n_med} total requested)
    // -----------------------------------------------------
"""
    for i in range(1, n_med + 1):
        v_code += f"    wire [7:0] internal_pipeline_stage_{i};\n"
        
    v_code += "\n    // Read them so they propagate to the valid_flag output\n"
    v_code += "    always @(posedge clk) begin\n"
    if n_med > 0:
        v_code += "        valid_flag <= " + " ^ ".join([f"internal_pipeline_stage_{i}[0]" for i in range(1, n_med + 1)]) + ";\n"
    else:
        v_code += "        valid_flag <= clk;\n"
    v_code += "    end\n\n"
    
    v_code += f"""    // -----------------------------------------------------
    // LOW PRIORITY BUGS ({n_low} total requested)
    // -----------------------------------------------------
"""
    for i in range(1, unused_amount + 1):
        v_code += f"    wire unused_diagnostic_{i};\n"
        # Driving them so they don't count as undriven!
        v_code += f"    assign unused_diagnostic_{i} = stream_in[{i % 31}];\n"
        
    v_code += "\nendmodule\n"
    
    with open(os.path.join(dir_path, f"{mod_name}.v"), "w") as f:
        f.write(v_code)
        
    ext_issues = []
    # Add external Highs (Uses unique bug types to avoid dedup)
    for i in range(json_highs):
        ext_issues.append({
            "type": f"Severe_Constraint_Fail_{i+1}",
            "signal": "valid_flag",
            "module": mod_name,
            "confidence": 0.99,
            "description": f"Critical routing or constraint failure #{i+1} reaching output."
        })
        
    # Add external Low
    ext_issues.append({
        "type": "naming_convention",
        "signal": "unused_diagnostic_1" if unused_amount > 0 else "clk",
        "module": mod_name,
        "confidence": 0.40,
        "description": "Signal suffix violation: expected standard '_dbg' suffix."
    })
    
    with open(os.path.join(dir_path, "detected_issues.json"), "w") as f:
        json.dump(ext_issues, f, indent=2)

print("Generated explicitly customized datasets successfully!")

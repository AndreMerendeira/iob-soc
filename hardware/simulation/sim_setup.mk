#
# This file segment is included in LIB_DIR/Makefile
#
# SIMULATION HARDWARE
#

AXI_GEN ?=$(LIB_DIR)/software/python/axi_gen.py
TB_DIR:=$(SOC_DIR)/hardware/simulation/verilog_tb

# HEADERS

#axi portmap for axi ram
SRC+=$(BUILD_SIM_DIR)/s_axi_portmap.vh
$(BUILD_SIM_DIR)/s_axi_portmap.vh:
	$(AXI_GEN) axi_portmap 's_' 's_' 'm_' && mv s_axi_portmap.vh $@


# SOURCES 

#axi memory
include $(LIB_DIR)/hardware/axiram/hardware.mk

SRC+=$(BUILD_SIM_DIR)/cpu_tasks.v
$(BUILD_SIM_DIR)/cpu_tasks.v: $(SOC_DIR)/hardware/include/cpu_tasks.v
	cp $< $@

SRC+=$(BUILD_SIM_DIR)/system_tb.v $(BUILD_SIM_DIR)/system_top.v

$(BUILD_SIM_DIR)/system_tb.v: $(SOC_DIR)/hardware/simulation/verilog_tb/system_core_tb.v
	$(SOC_DIR)/software/python/createTestbench.py $(SOC_DIR) "$(GET_DIRS)" "$(PERIPHERALS)" && mv system_tb.v $@

#create simulation top module
$(BUILD_SIM_DIR)/system_top.v: $(SOC_DIR)/hardware/simulation/verilog_tb/system_top_core.v
	$(SOC_DIR)/software/python/createTopSystem.py $(SOC_DIR) "$(GET_DIRS)" "$(PERIPHERALS)" && mv system_top.v $@

SRC+=$(BUILD_SIM_DIR)/iob_soc_tb.cpp
$(BUILD_SIM_DIR)/iob_soc_tb.cpp: $(SOC_DIR)/hardware/simulation/verilator/iob_soc_tb.cpp
	cp $< $@

#
# SCRIPTS
#
SRC+=$(BUILD_SW_PYTHON_DIR)/makehex.py $(BUILD_SW_PYTHON_DIR)/hex_split.py
$(BUILD_SW_PYTHON_DIR)/%.py: $(LIB_DIR)/software/python/%.py
	cp $< $@

SRC+=$(BUILD_SW_PYTHON_DIR)/hw_defines.py
$(BUILD_SW_PYTHON_DIR)/hw_defines.py: $(LIB_DIR)/software/python/hw_defines.py
	cp $< $@
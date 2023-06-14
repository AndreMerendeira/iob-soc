#!/usr/bin/env python3
import sys
import os

from iob_soc_create_periphs_tmp import create_periphs_tmp
from iob_soc_create_system import create_systemv
from iob_soc_create_sim_wrapper import create_sim_wrapper
from submodule_utils import get_table_ports, add_prefix_to_parameters_in_port, eval_param_expression_from_config, iob_soc_peripheral_setup, reserved_signals
from ios import get_interface_mapping
import setup
import iob_colors
import shutil
import fnmatch
import if_gen
import verilog_tools
import build_srcs

######################################
# Specialized IOb-SoC setup functions.
######################################

def iob_soc_sw_setup(python_module, exclude_files=[]):
    peripherals_list = python_module.peripherals
    confs = python_module.confs
    build_dir = python_module.build_dir
    name = python_module.name

    # Build periphs_tmp.h
    if peripherals_list: create_periphs_tmp(next(i['val'] for i in confs if i['name'] == 'P'),
                                   peripherals_list, f"{build_dir}/software/{name}_periphs.h")

def iob_soc_sim_setup(python_module, exclude_files=[]):
    peripherals_list = python_module.peripherals
    confs = python_module.confs
    build_dir = python_module.build_dir
    name = python_module.name
    # Try to build simulation <system_name>_sim_wrapper.v if template <system_name>_sim_wrapper.v is available and iob_soc_sim_wrapper.v not in exclude list
    if not fnmatch.filter(exclude_files,'iob_soc_sim_wrapper.v'):
        create_sim_wrapper(build_dir, name, python_module.ios, confs)

def iob_soc_doc_setup(python_module, exclude_files=[]):
    # Copy .odg figures without processing
    shutil.copytree(os.path.join(os.path.dirname(__file__),'..', "document/"),
            os.path.join(python_module.build_dir,"document/"), dirs_exist_ok=True,
            ignore=lambda directory, contents: [f for f in contents if os.path.splitext(f)[1] not in ['.odg', '']])

def iob_soc_hw_setup(python_module, exclude_files=[]):
    peripherals_list = python_module.peripherals
    build_dir = python_module.build_dir
    name = python_module.name

    # Try to build <system_name>.v if template <system_name>.v is available and iob_soc.v not in exclude list
    # Note, it checks for iob_soc.v in exclude files, instead of <system_name>.v to be consistent with the copy_common_files() function.
    #[If a user does not want to build <system_name>.v from the template, then he also does not want to copy the template from the iob-soc]
    if not fnmatch.filter(exclude_files,'iob_soc.v'):
        create_systemv(build_dir, name, peripherals_list, internal_wires=python_module.internal_wires)

######################################

# Run specialized iob-soc setup sequence
def setup_iob_soc(python_module):
    confs = python_module.confs
    build_dir = python_module.build_dir
    name = python_module.name

    # Replace IOb-SoC name in values of confs
    for conf in confs:
        if type(conf['val']) == str:
            conf['val'] = conf['val'].replace('iob_soc',name).replace('IOB_SOC',name.upper())

    # Setup peripherals
    iob_soc_peripheral_setup(python_module)
    python_module.internal_wires = peripheral_portmap(python_module)

    # Call setup function for iob_soc
    setup.setup(python_module)

    # Run iob-soc specialized setup sequence
    iob_soc_sim_setup(python_module)
    iob_soc_sw_setup(python_module)
    iob_soc_hw_setup(python_module)
    iob_soc_doc_setup(python_module)

    if python_module.is_top_module:
        verilog_tools.replace_includes(python_module.setup_dir, build_dir)

    # Check if was setup with INIT_MEM and USE_EXTMEM (check if macro exists)
    extmem_macro = next((i for i in confs if i['name']=='USE_EXTMEM'), False)
    initmem_macro = next((i for i in confs if i['name']=='INIT_MEM'), False)
    mem_add_w_parameter = next((i for i in confs if i['name']=='MEM_ADDR_W'), False)
    if extmem_macro and extmem_macro['val'] and \
       initmem_macro and initmem_macro['val']:
        # Append init_ddr_contents.hex target to sw_build.mk
        with open(f"{build_dir}/software/sw_build.mk", 'a') as file:
            file.write("\n#Auto-generated target to create init_ddr_contents.hex\n")
            file.write("HEX+=init_ddr_contents.hex\n")
            file.write("# init file for external mem with firmware of both systems\n")
            file.write(f"init_ddr_contents.hex: {name}_firmware.hex\n")

            sut_firmware_name = python_module.sut_fw_name.replace('.c','.hex') if 'sut_fw_name' in python_module.__dict__.keys() else '-'
            file.write(f"	../../scripts/joinHexFiles.py {sut_firmware_name} $^ {mem_add_w_parameter['val']} > $@\n")
        # Copy joinHexFiles.py from LIB
        build_srcs.copy_files( "submodules/LIB", f"{build_dir}/scripts", [ "joinHexFiles.py" ], '*.py' )


#Given the io dictionary of ports, the port name (and size, and optional bit list) and a wire, it will map the selected bits of the port to the given wire.
#io_dict: dictionary where keys represent port names, values are the mappings
#port_name: name of the port to map
#port_size: size the port (if port_bits are not specified, this value is not used)
#port_bits: list of bits of the port that are being mapped to the wire. If list is empty it will map all the bits.
#           The order of bits in this list is important. The bits of the wire will always be filled in incremental order and will match the corresponding bit of the port given on this list following the list order. Example: The list [5,3] will map the port bit 5 to wire bit 0 and port bit 3 to wire bit 1.
#wire_name: name of the wire to connect the bits of the port to.
def map_IO_to_wire(io_dict, port_name, port_size, port_bits, wire_name):
    if not port_bits:
        assert port_name not in io_dict, f"{iob_colors.FAIL}Peripheral port {port_name} has already been previously mapped!{iob_colors.ENDC}"
        # Did not specify bits, connect all the entire port (all the bits)
        io_dict[port_name] = wire_name
    else:
        # Initialize array with port_size, all bits with 'None' value (not mapped)
        if port_name not in io_dict: io_dict[port_name] = [None for n in range(int(port_size))]
        # Map the selected bits to the corresponding wire bits
        # Each element in the bit list of this port will be a tuple containign the name of the wire to connect to and the bit of that wire.
        for wire_bit, bit in enumerate(port_bits):
            assert bit < len(io_dict[port_name]), f"{iob_colors.FAIL}Peripheral port {port_name} does not have bit {bit}!{iob_colors.ENDC}"
            assert not io_dict[port_name][bit], f"{iob_colors.FAIL}Peripheral port {port_name} bit {bit} has already been previously mapped!{iob_colors.ENDC}"
            io_dict[port_name][bit] = (wire_name, wire_bit)

# Function to handle portmap connections between: peripherals, internal, and external system interfaces.
def peripheral_portmap(python_module):
    peripherals_list = python_module.peripherals
    ios = python_module.ios
    peripheral_portmap = python_module.peripheral_portmap

    # Add default portmap for peripherals not configured in peripheral_portmap
    for peripheral in peripherals_list:
        if peripheral.name not in [i[0]['corename'] for i in peripheral_portmap or []]+[i[1]['corename'] for i in peripheral_portmap or []]:
            # Import module of one of the given core types (to access its IO)
            module = peripheral.module
            # Map all ports of all interfaces
            for interface in module.ios:
                # If table has 'doc_only' attribute set to True, skip it
                if "doc_only" in interface.keys() and interface["doc_only"]:
                    continue

                if interface['ports']:
                    for port in interface['ports']:
                        if port['name'] not in reserved_signals:
                            # Map port to the external system interface
                            peripheral_portmap.append(({'corename':peripheral.name, 'if_name':interface['name'], 'port':port['name'], 'bits':[]}, {'corename':'external', 'if_name':peripheral.name, 'port':'', 'bits':[]}))
                else: 
                    # Auto-map if_gen interfaces, except for the ones that have reserved signals.
                    if interface['name'] in if_gen.interfaces and interface['name'] not in ['iob_s_port','axi_m_port']:
                        # Map entire interface to the external system interface
                        peripheral_portmap.append(({'corename':peripheral.name, 'if_name':interface['name'], 'port':'', 'bits':[]}, {'corename':'external', 'if_name':peripheral.name, 'port':'', 'bits':[]}))

    # Add 'IO" attribute to every peripheral
    for peripheral in peripherals_list:
        peripheral.io={}

    # List of peripheral interconnection wires
    peripheral_wires = []

    #Handle peripheral portmap
    for map_idx, mapping in enumerate(peripheral_portmap):
        # List to store both items in this mamping
        mapping_items = [None, None]
        assert mapping[0]['corename'] and mapping[1]['corename'], f"{iob_colors.FAIL}Mapping 'corename' can not be empty on portmap index {map_idx}!{iob_colors.ENDC}"

        # The 'external' keyword in corename is reserved to map signals to the external interface, causing it to create a system IO port
        # The 'internal' keyword in corename is reserved to map signals to the internal interface, causing it to create an internal system wire

        # Get system block of peripheral in mapping[0]
        if mapping[0]['corename'] not in ['external','internal']:
            assert any(i for i in peripherals_list if i.name == mapping[0]['corename']), f"{iob_colors.FAIL}{map_idx} Peripheral instance named '{mapping[0]['corename']}' not found!{iob_colors.ENDC}"
            mapping_items[0]=next(i for i in peripherals_list if i.name == mapping[0]['corename'])

        # Get system block of peripheral in mapping[1]
        if mapping[1]['corename'] not in ['external','internal']:
            assert any(i for i in peripherals_list if i.name == mapping[1]['corename']), f"{iob_colors.FAIL}{map_idx} Peripheral instance named '{mapping[1]['corename']}' not found!{iob_colors.ENDC}"
            mapping_items[1]=next(i for i in peripherals_list if i.name == mapping[1]['corename'])

        #Make sure we are not mapping two external or internal interfaces
        assert mapping_items != [None, None], f"{iob_colors.FAIL}{map_idx} Cannot map between two internal/external interfaces!{iob_colors.ENDC}"

        # By default, store -1 if we are not mapping to external/internal interface
        mapping_external_interface = -1
        mapping_internal_interface = -1

        # Store index if any of the entries is the external/internal interface
        if None in mapping_items:
            if mapping[mapping_items.index(None)]['corename'] == 'external':
                mapping_external_interface = mapping_items.index(None)
            else:
                mapping_internal_interface = mapping_items.index(None)

        # Create interface for this portmap if it is connected to external interface
        if mapping_external_interface>-1:
            # List of system IOs from ports of this mapping
            mapping_ios=[]
            # Add peripherals table to ios of system
            assert mapping[mapping_external_interface]['if_name'], f"{iob_colors.FAIL}Portmap index {map_idx} needs an interface name for the 'external' corename!{iob_colors.ENDC}"
            ios.append({'name': mapping[mapping_external_interface]['if_name'], 'descr':f"IOs for peripherals based on portmap index {map_idx}", 'ports': mapping_ios,
                        # Only set `ios_table_prefix` if user has not specified a value in the portmap entry
                        'ios_table_prefix':True if 'ios_table_prefix' not in mapping[mapping_external_interface] else mapping[mapping_external_interface]['ios_table_prefix']})

        # Import module of one of the given core types (to access its IO)
        module = mapping_items[0].module
        #print(f"DEBUG: {module.name} {module.ios}", file=sys.stderr)

        #Get ports of configured interface
        interface_table = next((i for i in module.ios if i['name'] == mapping[0]['if_name']), None) 
        assert interface_table, f"{iob_colors.FAIL}Interface {mapping[0]['if_name']} of {mapping[0]['corename']} not found!{iob_colors.ENDC}"
        interface_ports=get_table_ports(interface_table)

        #If mapping_items[1] is not internal/external interface
        if mapping_internal_interface!=1 and mapping_external_interface!=1: 
            # Import module of one of the given core types (to access its IO)
            module2 = mapping_items[1].module
            #Get ports of configured interface
            interface_table = next((i for i in module2.ios if i['name'] == mapping[1]['if_name']), None) 
            assert interface_table, f"{iob_colors.FAIL}Interface {mapping[1]['if_name']} of {mapping[1]['corename']} not found!{iob_colors.ENDC}"
            interface_ports2=get_table_ports(interface_table)

        # Check if should insert one port or every port in the interface
        if not mapping[0]['port']:
            # Mapping configuration did not specify a port, therefore insert all signals from interface and auto-connect them
            #NOTE: currently mapping[1]['if_name'] is always assumed to be equal to mapping[0]['if_name']

            # Get mapping for this interface
            if_mapping = get_interface_mapping(mapping[0]['if_name'])

            # For every port: create wires and connect IO
            for port in interface_ports:
                if mapping_internal_interface<0 and mapping_external_interface<0:
                    # Not mapped to internal/external interface
                    # Create peripheral wire name based on mapping.
                    wire_name = f"connect_{mapping[0]['corename']}_{mapping[0]['if_name']}_{port['name']}_to_{mapping[1]['corename']}_{mapping[1]['if_name']}_{if_mapping[port['name']]}"
                    peripheral_wires.append({'name':wire_name, 'n_bits':add_prefix_to_parameters_in_port(port,module.confs,mapping[0]['corename']+"_")['n_bits']})
                elif mapping_internal_interface>-1:
                    #Mapped to internal interface
                    #Wire name generated the same way as ios inserted in verilog 
                    if mapping_internal_interface==0:
                        wire_name = f"{mapping[0]['if_name']+'_'}{port['name']}"
                    else:
                        wire_name = f"{mapping[1]['if_name']+'_'}{port['name']}"
                    #Add internal system wire for this port
                    peripheral_wires.append({'name':wire_name, 'n_bits':add_prefix_to_parameters_in_port(port,module.confs,mapping[0]['corename']+"_")['n_bits']})

                else:
                    #Mapped to external interface
                    #Add system IO for this port
                    mapping_ios.append(add_prefix_to_parameters_in_port(port,module.confs,mapping[0]['corename']+"_"))
                    # Dont add `if_name` prefix if `iob_table_prefix` is set to False
                    if 'ios_table_prefix' in mapping[mapping_external_interface] and not mapping[mapping_external_interface]['ios_table_prefix']:
                        signal_prefix = ""
                    else:
                        signal_prefix = mapping[mapping_external_interface]['if_name']+'_'

                    if 'remove_string_from_port_names' in mapping[mapping_external_interface]:
                        signal_name = port['name'].replace(mapping[mapping_external_interface]['remove_string_from_port_names'],"")
                        # Update port name previsously inserted in mapping_ios
                        mapping_ios[-1]['name'] = signal_name
                    else:
                        signal_name = port['name']
                    #Wire name generated the same way as ios inserted in verilog 
                    wire_name = f"{signal_prefix}{signal_name}"

                #Insert mapping between IO and wire for mapping[0] (if its not internal/external interface)
                if mapping_internal_interface!=0 and mapping_external_interface!=0:
                    map_IO_to_wire(mapping_items[0].io, port['name'], 0, [], wire_name)

                #Insert mapping between IO and wire for mapping[1] (if its not internal/external interface)
                if mapping_internal_interface!=1 and mapping_external_interface!=1:
                    map_IO_to_wire(mapping_items[1].io, if_mapping[port['name']], 0, [], wire_name)

        else:
            # Mapping configuration specified a port, therefore only insert singal for that port

            port = next((i for i in interface_ports if i['name'] == mapping[0]['port']),None)
            assert port, f"{iob_colors.FAIL}Port {mapping[0]['port']} of {mapping[0]['if_name']} for {mapping[0]['corename']} not found!{iob_colors.ENDC}"

            if mapping_internal_interface!=1 and mapping_external_interface!=1: 
                port2 = next((i for i in interface_ports2 if i['name'] == mapping[1]['port']), None)
                assert port2, f"{iob_colors.FAIL}Port {mapping[1]['port']} of {mapping[1]['if_name']} for {mapping[1]['corename']} not found!{iob_colors.ENDC}"

            #Get number of bits for this wire. If 'bits' was not specified, use the same size as the port of the peripheral
            if not mapping[0]['bits']:
                # Mapping did not specify bits, use the same size as the port (will map all bits of the port)
                n_bits = port['n_bits']
            else:
                # Mapping specified bits, the width will be the total amount of bits specified
                n_bits = len(mapping[0]['bits'])
                # Insert wire of the ports into the peripherals_wires list of the system

            if mapping_internal_interface<0 and mapping_external_interface<0:
                # Not mapped to external interface
                # Create wire name based on mapping
                wire_name = f"connect_{mapping[0]['corename']}_{mapping[0]['if_name']}_{mapping[0]['port']}_to_{mapping[1]['corename']}_{mapping[1]['if_name']}_{mapping[1]['port']}"
                peripheral_wires.append({'name':wire_name, 'n_bits':add_prefix_to_parameters_in_port(port,module.confs,mapping[0]['corename']+"_")['n_bits']})
            elif mapping_internal_interface>-1:
                #Mapped to internal interface
                #Wire name generated the same way as ios inserted in verilog 
                if mapping_internal_interface==0:
                    wire_name = f"{mapping[0]['if_name']+'_'}{port['name']}"
                else:
                    wire_name = f"{mapping[1]['if_name']+'_'}{port['name']}"
                #Add internal system wire for this port
                peripheral_wires.append({'name':wire_name, 'n_bits':add_prefix_to_parameters_in_port(port,module.confs,mapping[0]['corename']+"_")['n_bits']})
            else:
                #Mapped to external interface
                #Add system IO for this port
                mapping_ios.append(add_prefix_to_parameters_in_port({'name':port['name'], 'type':port['type'], 'n_bits':n_bits, 'descr':port['descr']},
                                                                           module.confs,mapping[0]['corename']+"_"))
                # Dont add `if_name` prefix if `iob_table_prefix` is set to False
                if 'ios_table_prefix' in mapping[mapping_external_interface] and not mapping[mapping_external_interface]['ios_table_prefix']:
                    signal_prefix = ""
                else:
                    signal_prefix = mapping[mapping_external_interface]['if_name']+'_'

                if 'remove_string_from_port_names' in mapping[mapping_external_interface]:
                    signal_name = port['name'].replace(mapping[mapping_external_interface]['remove_string_from_port_names'],"")
                    # Update port name previsously inserted in mapping_ios
                    mapping_ios[-1]['name'] = signal_name
                else:
                    signal_name = port['name']
                #Wire name generated the same way as ios inserted in verilog 
                wire_name = f"{signal_prefix}{signal_name}"

            #Insert mapping between IO and wire for mapping[0] (if its not internal/external interface)
            if mapping_internal_interface!=0 and mapping_external_interface!=0:
                map_IO_to_wire(mapping_items[0].io, mapping[0]['port'], eval_param_expression_from_config(port['n_bits'],module.confs,'max'), mapping[0]['bits'], wire_name)

            #Insert mapping between IO and wire for mapping[1] (if its not internal/external interface)
            if mapping_internal_interface!=1 and mapping_external_interface!=1:
                map_IO_to_wire(mapping_items[1].io, mapping[1]['port'], eval_param_expression_from_config(port2['n_bits'],module2.confs,'max'), mapping[1]['bits'], wire_name)

    # Merge interfaces with the same name into a single interface
    interface_names = []
    for interface in ios:
        if interface['name'] not in interface_names:
            interface_names.append(interface['name'])
    new_ios = []
    for interface_name in interface_names:
        first_interface_instance = None
        for interface in ios:
            if interface['name'] == interface_name:
                if not first_interface_instance:
                    first_interface_instance = interface
                    new_ios.append(interface)
                else:
                    first_interface_instance['ports']+=interface['ports']
    python_module.ios=new_ios
    #print(f"### Debug python_module.ios: {python_module.ios}", file=sys.stderr)

    return peripheral_wires


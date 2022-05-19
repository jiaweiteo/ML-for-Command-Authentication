# The main function of this class is to create a network (net object) and allow updates to each component
# in the network.

# Changes:
# 16/12/2020: Changed a distance from 0.05 to 0.005 for single substation

import pandapower as pp
import os
import pandapower.shortcircuit as sc
import pandapower.estimation as est

import sys
import time
import pandapower_mapping
import logging
from enum import IntEnum

# Define the logger
logging.basicConfig(filename='pandapower_log.log', level=logging.INFO)
logger = logging.getLogger('pandapower_net.py')

class Device_Type(IntEnum):
	BUS = 0
	LINE = 1
	TRANSFORMER = 2
	UNKNOWN = -1

class Pandapower_Net:
	def __init__(self):
		pass
#------------------------------------------Static Methods----------------------------------------------------#
	# Read model from file
	@staticmethod
	def net_read_from_pickle():
		return pp.from_pickle("./network.p")

	# Write model to file
	@staticmethod
	def net_write_to_pickle(net):
		pp.to_pickle(net, "./network.p")

	# Read model from JSON file
	@staticmethod
	def net_read_from_json():
		return pp.from_json("./network.json")

	# Write model to JSON file
	@staticmethod
	def net_write_to_json(net):
		pp.to_json(net, "./network.json")

	# Get mapping from pandapower_mapping.py
	@staticmethod
	def net_modbus_get_mapping(modbus_num):
		if modbus_num in pandapower_mapping.modbus_unit_number_mappings:
			return pandapower_mapping.modbus_unit_number_mappings[modbus_num]

	# Get element identifier
	@staticmethod
	def net_get_modbus_name(modbus_num):
		#device_type, device_id = net_get_modbus_type_with_id(modbus_num)
		mapping = Pandapower_Net.net_modbus_get_mapping(modbus_num)
		device_type = mapping['element']
		device_id = mapping['idx']

		if device_type == Device_Type.BUS:
			return 'Bus '+ str(device_id)
		elif device_type == Device_Type.LINE:
			return 'Line ' + str(device_id)
		elif device_type == Device_Type.TRANSFORMER:
			return 'Transformer ' + str(device_id)
		else:
			return 'Unknown Element Name'
	
	# Get switch/transformer status (might be a bit confusing though, which is why usually I just use net.switch and net.line directly)
	@staticmethod
	def net_get_cb_status():
		net = Pandapower_Net.net_read_from_pickle()
		results = []		
		for i in net.switch.index:
			results.append('Line ' + str(net.switch["element"][i]))
			results.append("1" if (net.switch["closed"][i])==True else "0")
		for i in net.trafo.index:
			results.append('Transformer ' + str(net.trafo["name"][i]))
			results.append("1" if (net.trafo["in_service"][i])==True else "0")		
		return results	

	# Enable/disable element
	@staticmethod
	def net_modbus_update(modbus_num, command):
		results = []
		mapping = Pandapower_Net.net_modbus_get_mapping(modbus_num)
		device_type = mapping['element']
		device_id = mapping['idx']

		if device_type == Device_Type.LINE:
			return Pandapower_Net.net_switch_enable(device_id) if command==1 else Pandapower_Net.net_switch_disable(device_id)

		elif device_type == Device_Type.TRANSFORMER: 
			return Pandapower_Net.net_transformer_enable(device_id) if command==1 else Pandapower_Net.net_transformer_disable(device_id)

		else:
			return ["Unable to map modbus unit to device"]

	# Disable transformer
	@staticmethod
	def net_transformer_disable(trafo_num):
		net = Pandapower_Net.net_read_from_pickle()
		net.trafo["in_service"][trafo_num]=False

		Pandapower_Net.net_write_to_pickle(net)
		logger.info("Updated Status\n" + net.trafo.to_string())
		return 	['Transformer ' + str(trafo_num), str(0)]

	# Enable transformer
	@staticmethod
	def net_transformer_enable(trafo_num):
		net = Pandapower_Net.net_read_from_pickle()
		net.trafo["in_service"][trafo_num]=True

		Pandapower_Net.net_write_to_pickle(net)
		logger.info("Updated Status\n" + net.trafo.to_string())
		return ['Transformer ' + str(trafo_num), str(1)]
	
	# Disable switch
	@staticmethod
	def net_switch_disable(sw_num):
		# sw_num is equivalent to line number. So as not to have to make 2 requests for operation and cb status,
		# this function returns 2 results
		net = Pandapower_Net.net_read_from_pickle()
		net.switch["closed"][sw_num]=False
		Pandapower_Net.net_write_to_pickle(net)
		logger.info("Updated Status\n" + net.switch.to_string())
		
		return ['Line ' + str(sw_num), str(0), pandapower_mapping.load_elements_line_cb_name[sw_num] if sw_num in pandapower_mapping.load_elements_line_cb_name else None]

	# Enable switch
	@staticmethod
	def net_switch_enable(sw_num):
		net = Pandapower_Net.net_read_from_pickle()
		net.switch["closed"][sw_num]=True
		Pandapower_Net.net_write_to_pickle(net)
		logger.info("Updated Status\n" + net.switch.to_string())

		return ['Line ' + str(sw_num), str(1), pandapower_mapping.load_elements_line_cb_name[sw_num] if sw_num in pandapower_mapping.load_elements_line_cb_name else None]

#----------------------------------------Non-Static Methods--------------------------------------------------#
	# Create a new template model and save it to file
	def execute(self):
		self.create_example_net()
		self.net_write_to_pickle(self.net)
		#self.net_write_to_json(self.net) #Prints 'DataFrame' multiple times
		
	# NOTE: There is a hard dependency here between line and switch indexes.
	# Currently still acceptable so long as we don't have multiple switches per line that need to be controlled,
	# and we don't control bus-bus switches
	def create_line_with_switch(self, l_index, first_bus, last_bus, length_km, std_type):
		lidx = pp.create_line(self.net, first_bus, last_bus, index=l_index, std_type=std_type, length_km=length_km)
		sw = pp.create_switch(self.net, bus=first_bus, element=lidx, et="l", index=l_index, closed=True)

	# Create template model and save it in this object
	def create_example_net(self):
		# 3 Substations Configuration
		#-------------------------------------
		# Substation 1
		#------------------------------------
		# An empty network object is created, that will be filled in the next steps.
		self.net = pp.create_empty_network()
		
		# Define initial p and q values using bus index mapping
		self.load_elements_bus_init_values = {
			#4: [3, 0.8], 5: [2.5, 0.6],
			#6: [4.0, 0.9], 7: [3.5, 0.5],
			10: [1.0, 0.2], 11: [1.1, 0.3],
			12: [0.9, 0.1], 13: [1.2, 0.3],
			14: [0.8, 0.2], 15: [1.0, 0.1],
		}

		# create slack nodes
		grb = pp.create_buses(self.net, nr_buses=2, index=[0, 1], vn_kv=110.0)
		pp.create_ext_grid(self.net, grb[0], s_sc_min_mva=1500, rx_min=0.3) # Generator on Bus 0
		pp.create_ext_grid(self.net, grb[1], s_sc_min_mva=2500, rx_min=0.3) # Generator on Bus 1

		# define the standard types for this network
		std_types = ["N2XS(FL)2Y 1x300 RM/35 64/110 kV", "NA2XS2Y 1x240 RM/25 6/10 kV"]

		# create 110kV bus network
		hvb = pp.create_buses(self.net, nr_buses=6, index=[2,3,4,5,6,7], vn_kv=110.0)

		fb = [0,2,2,2,1,3,3]
		lb = [2,4,5,3,3,6,7]
		#length = [0.05, 0.4, 0.6, 0.05, 0.05, 0.7, 0.8]
		length = [0.05, 2, 1.5, 0.05, 0.05, 1.5, 2] # Increased distance for 4 lines.
		
		for i in range(7):
		   self.create_line_with_switch(l_index=i, first_bus=fb[i], last_bus=lb[i], length_km=length[i], std_type=std_types[0])

		# create 10kV bus network
		mvb = pp.create_buses(self.net, nr_buses=8, index=[8, 9, 10, 11, 12, 13, 14, 15], vn_kv=10.0)

		fb = [8, 8, 8, 8, 9, 9, 9]
		lb = [10, 11, 12, 9, 13, 14, 15]
		length = [0.3, 0.2, 0.1, 0.005, 0.2, 0.3, 0.1]
		for i in range(7):
			self.create_line_with_switch(l_index=i+7, first_bus=fb[i], last_bus=lb[i], length_km=length[i], std_type=std_types[1])

		# Create transformers
		pp.create_transformer(self.net, hv_bus=2, lv_bus=8, std_type="25 MVA 110/10 kV", index=0, name="0")
		pp.create_transformer(self.net, hv_bus=3, lv_bus=9, std_type="25 MVA 110/10 kV", index=1, name="1")

		# Cables - defines max temperature for cable
		self.net.line.loc[self.net.line.index[self.net.line.type == "cs"], "endtemp_degree"] = 20

		# Create load elements on buses, populate the p and q
		for element in self.load_elements_bus_init_values:
			pp.create_load(self.net, element, self.load_elements_bus_init_values[element][0], self.load_elements_bus_init_values[element][1], name=element)
		
		#-------------------------------------
		# Substation 2 (Left)
		#-------------------------------------
		# new buses 16-17 (after trafo)
		hvb = pp.create_buses(self.net, nr_buses=2, index=[16,17], vn_kv=10.0)

		# Create transformers
		pp.create_transformer(self.net, hv_bus=5, lv_bus=16, std_type="25 MVA 110/10 kV", index=2, name="2")
		pp.create_transformer(self.net, hv_bus=6, lv_bus=17, std_type="25 MVA 110/10 kV", index=3, name="3")

		# Define initial p and q values using bus index mapping
		self.load_elements_bus_init_values = {
			20: [1.0, 0.2], 21: [1.1, 0.3],
			22: [0.9, 0.1], 23: [1.2, 0.3],
			24: [0.8, 0.2], 25: [1.0, 0.1],
			26: [0.9, 0.2], 27: [1.2, 0.1]
		}

		# create 10kV bus network (loads)
		mvb = pp.create_buses(self.net, nr_buses=8, index=[20,21,22,23,24,25,26,27], vn_kv=10.0)

		# Create load elements on buses, populate the p and q
		for element in self.load_elements_bus_init_values:
			pp.create_load(self.net, element, self.load_elements_bus_init_values[element][0], self.load_elements_bus_init_values[element][1], name=element)

		# New lines 14 - 21
		fb = [16, 16, 16, 16, 17, 17, 17, 17]
		lb = [20, 21, 22, 23, 24, 25, 26, 27]
		length = [0.3, 0.2, 0.1, 0.05, 0.2, 0.3, 0.1, 0.05]
		for i in range(8):
		   self.create_line_with_switch(l_index=i+14, first_bus=fb[i], last_bus=lb[i], length_km=length[i], std_type=std_types[1])
		   
		# Add another switch to extended lines L2, L5
		# CB-51 there's no line to line option. bus-bus/bus-line/bus-trafo.
		# The switch indexes created without line with be given #1 + cb-name
		pp.create_switch(self.net, bus=5, element=2, et="l", index=151)
		pp.create_switch(self.net, bus=6, element=5, et="l", index=152)
		
		# Add the Normally-Open (NO) switches
		pp.create_switch(self.net, bus=5, element=6, et="b", closed=False, index=153)
		pp.create_switch(self.net, bus=16, element=17, et="b", closed=False, index=158)
		
		#-------------------------------------
		# Substation 3 (Right)
		#-------------------------------------	
		# new buses 18-19 (after trafo)
		hvb = pp.create_buses(self.net, nr_buses=2, index=[18,19], vn_kv=10.0)

		# Create transformers
		pp.create_transformer(self.net, hv_bus=4, lv_bus=18, std_type="25 MVA 110/10 kV", index=4, name="4")
		pp.create_transformer(self.net, hv_bus=7, lv_bus=19, std_type="25 MVA 110/10 kV", index=5, name="5")

		# Define initial p and q values using bus index mapping
		self.load_elements_bus_init_values = {
			28: [1.0, 0.2], 29: [1.1, 0.3],
			30: [0.9, 0.1], 31: [1.2, 0.3],
		}

		# create 10kV bus network (loads)
		mvb = pp.create_buses(self.net, nr_buses=4, index=[28,29,30,31], vn_kv=10.0)

		# Create load elements on buses, populate the p and q
		for element in self.load_elements_bus_init_values:
			pp.create_load(self.net, element, self.load_elements_bus_init_values[element][0], self.load_elements_bus_init_values[element][1], name=element)

		# New lines 22 - 25
		fb = [18,18,19,19]
		lb = [28,29,30,31]
		length = [0.3, 0.2, 0.1, 0.05]
		for i in range(4):
		   self.create_line_with_switch(l_index=i+22, first_bus=fb[i], last_bus=lb[i], length_km=length[i], std_type=std_types[1])
		   
		# Add another switch to extended lines L1, L6. CB-71, CB-72.
		pp.create_switch(self.net, bus=4, element=1, et="l", index=171)
		pp.create_switch(self.net, bus=7, element=6, et="l", index=172)
		
		# Add the Normally-Open (NO) switches
		pp.create_switch(self.net, bus=4, element=7, et="b", closed=False, index=173)
		pp.create_switch(self.net, bus=18, element=19, et="b", closed=False, index=178)
		

if __name__ == "__main__":
	start_time = time.time()
	Pandapower_Net().execute()
	print("--- %s seconds ---" % (time.time() - start_time))

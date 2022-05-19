from datetime import datetime 
import pandapower.networks as pn
import pandapower as pp
import pandapower.estimation as est
import sys
import json
import time
import pandapower_mapping
import logging

from pandapower_net import Pandapower_Net
from pandapower_net import Device_Type

# Define the logger
logging.basicConfig(filename='pandapower_log.log', level=logging.INFO)
logger = logging.getLogger('pandapower_pf.py')

class Power_Flow:
	def __init__(self, load_dict, test_condition=[]):
		self.load_dict = load_dict
		self.load_percent_test = False
		self.test_condition = test_condition
	
	def execute(self):
		result_vector=[]
		self.net = Pandapower_Net.net_read_from_pickle()
		self.update_pq_loads()

		# A test condition refers to possible commands for which PF will be executed but will not be recorded in
		# the net object. It is to test the outcome and determine if it is favourable or not.
		if self.test_condition!=[]:
			self.update_test_condition()

		pp.runpp(self.net)

		#Run checks on result
		self.load_percent_test, result_msg = self.check_loading_percent_ok()

		logger.info("******************bus result************************\n" + (self.net.res_bus).to_string())
		logger.info("******************line result************************\n" + (self.net.res_line).to_string())
		logger.info("******************trafo result***********************\n" + (self.net.res_trafo).to_string())

		# test_condition format: [modbus_num, command]
		result_vector = [str(i) for i in self.test_condition]
		
		if self.test_condition!=[]:
			mapping = Pandapower_Net.net_modbus_get_mapping(self.test_condition[0])
			device_type = mapping['element']
			device_id = mapping['idx']
			#result_vector.append(pandapower_mapping.load_elements_line_cb_name[device_id])
			# If the key is non-existent, return value None
			result_vector.append(pandapower_mapping.load_elements_line_cb_name.get(device_id, "None"))

		return "Power Flow: " + result_msg, result_vector

	# Update the p&q values in this instance of net object
	def update_pq_loads(self):
		# update the p and q values of the load elements from bro in net
		for modbus_num,val in self.load_dict.items():
			dframe = self.net.load[self.net.load.bus==pandapower_mapping.modbus_unit_number_mappings[modbus_num]['idx']]
			if not dframe.empty:
				self.net.load["p_mw"][dframe.index[0]] = val[0]
				self.net.load["q_mvar"][dframe.index[0]] = val[1]

	# Update the test condition in this instance of net object
	def update_test_condition(self):		
		logger.info("Updating test condition " + str(self.test_condition))
		modbus_num = self.test_condition[0]
		command = self.test_condition[1]

		mapping = Pandapower_Net.net_modbus_get_mapping(modbus_num)
		device_type = mapping['element']
		device_id = mapping['idx']

		if device_type == Device_Type.LINE:
			self.net.switch["closed"][device_id] = command
		elif device_type == Device_Type.TRANSFORMER:
			self.net.trafo["in_service"][device_id] = command

	# This function checks the loading percentage of each bus in the network.
	# Returns True if all loading percentages are within the threshold.
	def check_loading_percent_ok(self):
		succeeded = True
		result = "Passed"
		for idx in self.net.res_line["loading_percent"].index:
			if(self.net.res_line["loading_percent"][idx] > 80):
				result = "High loading (%): " + str(self.net.res_line["loading_percent"][idx].round(2))
				logger.info (result)
				succeeded = False
		return succeeded, result


if __name__ == "__main__":
	logger.info("aaaaaa")
	start_time = time.time()
	#sample data
	Power_Flow({1: [-9.816, -1.359], 3: [-9.853, -1.268], 4: [3.0, 0.581], 5: [3.0, 0.8], 6: [2.5, 0.297], 7: [2.5, 0.6], 9: [0.0, 0.0], 10: [0.0, 0.0], 12: [4.0, 0.9], 14: [3.5, 0.5], 16: [0.0, 0.0], 17: [0.0, 0.0], 19: [1.0, 0.2], 20: [1.1, 0.297], 21: [1.1, 0.3], 22: [0.9, 0.099], 23: [0.9, 0.1], 24: [1.2, 0.297], 25: [1.2, 0.3], 26: [0.8, 0.196], 27: [0.8, 0.2], 28: [1.0, 0.099], 29: [1.0, 0.1]}).execute()
	print("--- %s seconds ---" % (time.time() - start_time))


import random
from pandapower_net import Pandapower_Net
import pandapower as pp
import math

##### Common class for all dataset generators

##### All generators have the same purpose of generating grid configurations with respective
##### power flow result status (i.e. whether results are within tolerable limits or anomalous)
##### However the different generators generate datapoints (different grid configurations) in
##### different ways - please refer to the respective files for more info
class Generator_Common:
	
	# Range of values that load values can take, as percentage of the originals defined in pandapower_net.py
	load_variance_limits = [70,110]
	# load_variance_limits = [70,100]


	# Number of d.p. to round to for load values
	load_rounding_degree = 4

	# Factor by which all loads should be multiplied (used to increase anomalous datapoint incidence)
	load_mult_factor = 2.8

	# List of buses with attached loads, for which the loads should be varied
	load_buses_to_vary = [10, 11, 12, 13, 14, 15, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]

	def __init__(self, output_file, datapoint_count):
		
		# Setup logger - to be redefined in subclasses
		self.setup_log()

		# Define output CSV file name to store datapoints
		self.output_file = output_file

		# Store number of datapoints to generate
		self.datapoint_count = datapoint_count
		return
	
	# Setup logger - to be redefined in subclasses
	def setup_log(self):
		raise RuntimeError('Generator_Common: setup_log(): abstract function - please define for subclasses')

		return
	
	def main(self):

		# Define new Pandapower_Net object (from pandapower_net.py), and use it to create a pandapower network
		# with default grid config
		pNet = Pandapower_Net()
		pNet.execute()

		# Extract the resulting pandapower network
		self.net = pNet.net
		# print(self.net)
		
		# Extract list of switches, loads, transformers and feeders
		self.initialize_idxs()

		# Initialize loads by storing values of loads in the default config multiplied by load_mult_factor
		self.initialize_loads()

		with open(self.output_file,"w") as f:
			
			# Get headers to identify the different values in a datapoint, and write them to the CSV file
			# as the first line
			headers = self.compile_headers()
			f.write(",".join(headers)+"\n")

			# Initialize number of successfully generated datapoints, generation failures and number of
			# datapoints with anomalous power flow test results respectively
			complete_point_count = 0
			error_count = 0
			anomaly_count = 0

			# Define thresholds to allow indication of progress
			# Every time about another 10% of datapoints are successfully generated, a message is printed in console
			progress_checkpoint_bar = self.datapoint_count//10
			
			while complete_point_count<self.datapoint_count:

				# Generate new datapoint
				# If successful, the function call returns a list, with the last element being "1" if the power
				# flow test result is anomalous and "0" otherwise
				# Otherwise the function returns None
				results = self.generate_new_datapoint()

				if results==None:
					error_count += 1

					# Run diagnostic on the datapoint in case of generation failure (as of writing this is
					# currently disabled in the subclasses' code)
					self.run_diagnostic()
					continue

				# Write results to CSV
				f.write(",".join(results)+"\n")
				complete_point_count+=1

				# Update anomalous datapoint counter
				anomaly_count+=int(results[-2])

				# Print progress indicator if appropriate
				if ((self.datapoint_count-complete_point_count)%progress_checkpoint_bar==0):
					print("Progress: {}%% complete".format(complete_point_count/self.datapoint_count*100))

			print("Program complete. Number of execution errors: {}".format(error_count))
			print("Anomalous datapoints: {}".format(anomaly_count))
		
		return

	# Get list of switches, loads, transformers and feeders (in all generators we tend to vary all to create
	# different configurations)
	def initialize_idxs(self):
		self.switch_idxs = list(self.net.switch.index)
	
		self.load_idxs = []
		for i in Generator_Common.load_buses_to_vary:
			# Get index of first load whose bus field is i
			self.load_idxs.append(self.net.load[self.net.load["bus"]==i].index[0])
		
		self.trafo_idxs = list(self.net.trafo.index)		
		self.feeder_idxs = list(self.net.ext_grid.index)
		# self.initial_load = []
		self.reason = []
		return
	
	# Initialize loads
	def initialize_loads(self):

		# Copy loads (as part of a DataFrame) to a generator's own object variable
		self.original_loads = self.net.load.copy()

		# Apply load_mult_factor on all loads in said DataFrame
		for i in self.original_loads.index:
			self.original_loads.at[i,"p_mw"] = self.original_loads.at[i,"p_mw"] * Generator_Common.load_mult_factor
			self.original_loads.at[i,"q_mvar"] = self.original_loads.at[i,"q_mvar"] * Generator_Common.load_mult_factor

		# print(self.original_loads)
		return

	def initialize_init_load(self):
		total_init_load = 0
		for idx in self.net.load.index:
			total_init_load += self.net.res_load["p_mw"][idx]

		self.initial_load = total_init_load

	
	# Get list of headers - note that the last field is always whether a datapoint is anomalous
	def compile_headers(self):
		headers = []

		for i in self.switch_idxs:
			headers.append("CB_{}_closed".format(i))

		for i in self.load_idxs:
			headers.append("load_{}::p".format(i))
			headers.append("load_{}::q".format(i))

		for i in self.trafo_idxs:
			headers.append("trafo_{}_in_service".format(i))
	
		for i in self.feeder_idxs:
			headers.append("feeder_{}_in_service".format(i))

		headers.append("total_init_load")

		headers.append("anomaly")

		headers.append("reason")

		return headers

	# Generate a new datapoint
	def generate_new_datapoint(self):

		# Clear results of any previous power flow simulation - otherwise power flow simulation might not converge
		self.clear_result()

		# Generate a random configuration for current datapoint
		self.vary_grid()
		

		# Run a power flow simulation - if simulation fails the pandapower library throws an exception
		try:
			pp.runpp(self.net,init='results')
	
		except:
			return None

		self.initialize_init_load()
		
		# Compile configuration details and power flow simulation result, and return it
		# return self.get_result_list()
		self.count += 1
		return self.get_result_list_modified(self.net, self.count)

	# Clear power flow simulation results (object method)
	def clear_result(self):
		Generator_Common.static_clear_result(self.net)

		return
	
	# Clear power flow simulation results (class method)
	def static_clear_result(net):

		# Clear all rows of the result dataframes, without deleting the dataframes themselves
		# Simply deleting them does not work as this would prevent future power flow test iterations
		net.res_bus = net.res_bus.iloc[0:0]
		net.res_line = net.res_line.iloc[0:0]
		net.res_trafo = net.res_trafo.iloc[0:0]
		net.res_ext_grid = net.res_ext_grid.iloc[0:0]
		net.res_load = net.res_load.iloc[0:0]

		return

	# Vary grid configuration for current datapoint
	def vary_grid(self):
		self.set_varied_loads()
		self.vary_grid_specific()
		
		return

	# Vary grid loads for current datapoint (object function version)
	def set_varied_loads(self):
		Generator_Common.static_set_varied_loads(self.load_idxs,self.original_loads,self.net)
		return

	# Vary grid loads for current datapoint (static version)
	def static_set_varied_loads(load_idxs,original_loads,net):
		for i in load_idxs:

			# Select random percentage between the lower and upper limits defined in load_variance_limits
			load_factor = random.uniform(Generator_Common.load_variance_limits[0],Generator_Common.load_variance_limits[1])/100
			net.load.at[i,"p_mw"] = original_loads.at[i,"p_mw"]*load_factor
			net.load.at[i,"q_mvar"] = original_loads.at[i,"q_mvar"]*load_factor
		
		return
	
	# Vary switch, transformer and feeder configurations - this is generator-specific and should be
	# concretized in subclasses
	def vary_grid_specific(self):
		raise RuntimeError('Generator_Common: vary_grid_specific(): abstract function - please define for subclasses')

		return
	
	# Helper function - create a random list of given length that has at least one instance of guaranteed_val
	# This is to guarantee at least 1 of any desired boolean value in a list of given length
	# Note that guaranteed_val can only be a boolean value
	# Note also that this is an object function
	def get_guarantee_min_1_list(self,length,guaranteed_val=True):
		return Generator_Common.static_get_guarantee_min_1_list(length,guaranteed_val)

	# Static version of above function
	def static_get_guarantee_min_1_list(length,guaranteed_val=True):
		pool = []
		
		for i in range(1,2**length):
			entry = []
			j = i

			for k in list(range(length))[::-1]:
				offset = 2**k
				if (j>=offset):
					j-=offset
					entry.append(guaranteed_val)
				else: entry.append(not guaranteed_val)
			pool.append(entry)
	
		return random.choice(pool)

	# Compile grid configuration for current datapoint and whether the datapoint has anomalous results,
	# to be written into the output CSV file
	def get_result_list(self):
		results = []
	
		for i in self.switch_idxs:
			results.append("1" if self.net.switch.at[i,"closed"] else "0")
		for i in self.load_idxs:
			results.append(str(round(self.net.res_load.at[i,"p_mw"],Generator_Common.load_rounding_degree)))
			results.append(str(round(self.net.res_load.at[i,"q_mvar"],Generator_Common.load_rounding_degree)))
		for i in self.trafo_idxs:
			results.append("1" if self.net.trafo.at[i,"in_service"] else "0")
		for i in self.feeder_idxs:
			results.append("1" if self.net.ext_grid.at[i,"in_service"] else "0")
	
		results.append("0" if self.check_result() else "1")

		return results

	# Determine whether datapoint power flow result is anomalous (object method)
	def check_result(self):
		
		return Generator_Common.static_check_result(self.net)

	# Determine whether datapoint power flow result is anomalous (class method)
	def static_check_result(net):
		# print(net.switch)
		# print(net.res_line)
		# Check line loading: lines should have 80% or less loading percent
		for idx in net.res_line.index:
			if (math.isnan(net.res_line["loading_percent"][idx])): continue
			if (net.res_line["loading_percent"][idx] > 80):
				return False

		# print(net.res_bus)
		# Check bus PU: >0.1 and <0.95 is too low, >1.05 is too high
		for idx in net.res_bus.index:
			if (math.isnan(net.res_bus["vm_pu"][idx])): continue
			if (net.res_bus["vm_pu"][idx]>1.05 or (net.res_bus["vm_pu"][idx]>0.1 and net.res_bus["vm_pu"][idx]<0.95)):
				return False

		# print(net.res_trafo)
		# Check trafo loading - transformers should have 80% or less loading percent
		for idx in net.res_trafo.index:
			if (math.isnan(net.res_trafo["loading_percent"][idx])): continue
			if (net.res_trafo["loading_percent"][idx] > 80):
				return False
 		
		return True

	def get_result_list_modified(self, net, count):
		results = []
	
		for i in self.switch_idxs:
			results.append("1" if self.net.switch.at[i,"closed"] else "0")
		for i in self.load_idxs:
			results.append(str(round(self.net.res_load.at[i,"p_mw"],Generator_Common.load_rounding_degree)))
			results.append(str(round(self.net.res_load.at[i,"q_mvar"],Generator_Common.load_rounding_degree)))
		for i in self.trafo_idxs:
			results.append("1" if self.net.trafo.at[i,"in_service"] else "0")
		for i in self.feeder_idxs:
			results.append("1" if self.net.ext_grid.at[i,"in_service"] else "0")

		results.append(str(self.initial_load))

		results.append("0" if self.check_result_modified(net) else "1")
		results.append(self.reason[count])
		return results

	# Determine whether datapoint power flow result is anomalous (object method)
	def check_result_modified(self, net):
		# print(net.switch)
		# print(net.res_line)

		#For attack data only
		# for idx in net.res_line.index:
		# 	if (idx >= 7 and idx < 25 and idx != 10) and math.isnan(net.res_line["loading_percent"][idx]): 
		# 		# print(idx)
		# 		self.reason.append("No power flowing through line {}: Circuit is open".format(idx))
		# 		return False

		# For attack data and randomly switching on/off switches
		# Check grid config still valid:
		validConfig = self.isValidConfig()
		if not validConfig[0]:
			self.reason.append("Config Violation: " + validConfig[1])
			return False
				
		# Check line loading: lines should have 80% or less loading percent
		for idx in net.res_line.index:
			if (math.isnan(net.res_line["loading_percent"][idx])): continue
			if (net.res_line["loading_percent"][idx] > 80):
				self.reason.append("Lines over 80%")
				return False

		# print(net.res_bus)
		# Check bus PU: >0.1 and <0.95 is too low, >1.05 is too high
		for idx in net.res_bus.index:
			if (math.isnan(net.res_bus["vm_pu"][idx])): continue
			if (net.res_bus["vm_pu"][idx]>1.05 or (net.res_bus["vm_pu"][idx]>0.1 and net.res_bus["vm_pu"][idx]<0.95)):
				self.reason.append("bus PU violated")
				return False

		# print(net.res_trafo)
		# Check trafo loading - transformers should have 80% or less loading percent
		for idx in net.res_trafo.index:
			if (math.isnan(net.res_trafo["loading_percent"][idx])): continue
			if (net.res_trafo["loading_percent"][idx] > 80):
				self.reason.append("Transformers over 80%")
				return False

		# print(net.res_load)
		# print(net.res_ext_grid)
		# Check open switches - Total switches open should not be more than 8
		count = 0
		for idx in net.switch.index:
			if count > 8:
				self.reason.append("More than 8 open switches")
				return False
			if (net.switch["closed"][idx] == False):
				count += 1

		#More than 20% of load lost compared against initial total load (Sum up p of all lines) --> Attack
		total_final_load = 0
		for idx in net.load.index:
			total_final_load += net.res_load["p_mw"][idx]
		
		if self.initial_load != 0:
			if (abs(self.initial_load - total_final_load) / self.initial_load) > 0.2:
				self.reason.append("Load Lost > 20%")
				return False

		self.reason.append("No anomaly")
		return True

	def isValidConfig(self):
		invalidConfig = [
			[False, False, False],
			[False, False, True],
			[False, True, False],
			[True, False, False]]

		SS1_Feeder = ["Feeder1", [0],[4],[3]]
		SS1_Trafo = ["Trafo1", [0],[1],[10]]
		SS2_Feeder = ["Feeder2", [2,151],[5,152],[153]]
		SS2_Trafo = ["Trafo2", [2],[3],[158]]
		SS3_Feeder = ["Feeder3", [1,171],[6,172],[173]]
		SS3_Trafo = ["Trafo3", [4],[5],[178]]

		allSS =  []
		allSS.append(SS1_Feeder)
		allSS.append(SS1_Trafo)
		allSS.append(SS2_Feeder)
		allSS.append(SS2_Trafo)
		allSS.append(SS3_Feeder)
		allSS.append(SS3_Trafo)

		#Check for invalid configuration for SS-1 Feeders:
		for substation_config in allSS:
			valid = self.validateConfig(substation_config)
			if not valid:
				return (False, substation_config[0])
		
		return (True, None)

	def validateConfig(self, ss_config):
		ss_type = ss_config[0]
		openCount = 0

		if "Feeder" in ss_type:
			for switchlist in ss_config[1:]:
				for switch in switchlist:
					if self.net.switch["closed"][switch] == False:
						openCount += 1
						break

		if "Trafo" in ss_type:
			for i in range(1, len(ss_config)):
				for switch in ss_config[i]:
					if i < 3 and self.net.trafo["in_service"][switch] == False:
						openCount += 1
						break
					if i == 3 and self.net.switch["closed"][switch] == False:
						openCount += 1
						break
		
		if openCount >= 2:
			return False #Invalid Config

		return True #Valid Config

	# Run diagnostic for generation failures - this method should be concretized in subclasses
	def run_diagnostic(self):
		raise RuntimeError('Generator_Common: run_diagnostic(): abstract function - please define for subclasses')

		return
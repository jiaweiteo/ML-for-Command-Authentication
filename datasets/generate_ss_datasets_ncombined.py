from generate_ss_datasets_common import Generator_Common
from pandapower_net import Pandapower_Net
import pandapower as pp
import copy
import random
import argparse
import time
import logging
import math

##### NCombined dataset generator
##### This generator makes use of the same constraints used in the constrained dataset generator,
##### and is in fact based on said generator, but works differently and serves different purposes

##### In terms of purpose, while the constrained generator aims to create unrelated datapoints,
##### this NCombined dataset aims to create sets of related datapoints where the first datapoint
##### in the set is always a non-anomalous datapoint and other datapoints in the set are related 
##### to it by having applying options sequentially to form new datapoints.

##### In terms of workings, while the constrained generator creates each datapoint individually,
##### this generator starts each set of datapoints by first creating a non-anomalous datapoint,
##### then repeatedly starting from this datapoint and pushing it towards an anomalous configuration
##### through the use of "options" that serve to push the grid towards upper loading percent/
##### voltage limits
class Generator_NCombined(Generator_Common):

	# List of default non-switch options (to push datapoint towards anomalous results)
	initial_options_base = ["feeder_0","feeder_1","feeder_2","trafo_0","trafo_1","trafo_2"]

	# Dictionary of elements to alter for initial feeder options
	feeder_config_set = {
		"feeder_0": {
			"feeders": [0,1],
			"switches": [[0],[4]],
			"couplers": []
		},
		"feeder_1": {
			"switches": [[2,151],[5,152]],
			"couplers": [153]
		},
		"feeder_2": {
			"switches": [[1,171],[6,172]],
			"couplers": [173]
		}
	}

	# Dictionary of elements to alter for initial trafo options
	trafo_config_set = {
		"trafo_0": {
			"trafos": [0,1],
			"couplers": []
		},
		"trafo_1": {
			"trafos": [2,3],
			"couplers": [158]
		},
		"trafo_2": {
			"trafos": [4,5],
			"couplers": [178]
		}
	}

	# List consisting of indexes for switches CB-100 and CB-200 - these switches are to be left alone
	static_switch_set = [3,10]

	# Number of options to be executed when making non-anomalous dataset
	initial_vary_count = 5

	# Initialization: also define maximum number of anomalous datapoints to create per non-anomalous datapoint
	def __init__(self,output_file,datapoint_count):
		super().__init__(output_file,datapoint_count)
		self.count = 0

		return

	# Setup logger
	def setup_log(self):
		logging.basicConfig(filename='pandapower_log.log', level=logging.INFO)
		self.logger = logging.getLogger('generate_ss_datasets_ncombined.py')

		return
	
	# Main execution flow of the generator - due to the difference in workings between this generator and
	# other generators, this function is redefined here
	def main(self):

		# Create new pandapower network and generate default grid configuration
		pNet = Pandapower_Net()
		pNet.execute()

		# Extract pandapower network object
		self.net = pNet.net
		
		# Compile indexes of (mostly) variable elements
		self.initialize_idxs()

		# Compile original list of loads
		self.initialize_loads()
		
		# Compile list of possible "options" (choices to push grid towards more anomalous state)
		self.initialize_options()

		# Turn off all loads (to emulate grid's safest state)
		# self.disable_all_loads()

		# Record the current grid configuration and available "options" list - this is to reset
		# the grid at the start of each datapoint set
		self.initial_state = self.record_state()

		with open(self.output_file,"w") as f:
			
			# Compile and write headers for CSV values
			headers = self.compile_headers()
			f.write(",".join(headers)+"\n")

			# Initialize counts for normal datapoints, generation failures and anomalous datapoints respectively
			normal_count = 0
			error_count = 0
			anomaly_count = 0

			# Define thresholds for number of normal datapoints to be generated, after each occurrence of which
			# a progress update will be shown in console
			progress_checkpoint_bar = self.datapoint_count//10
			
			while normal_count<self.datapoint_count:

				# Generate datapoint set - if generation error occurs (i.e. power flow on the initial datapoint fails)
				# then None is returned
				# Otherwise if initial datapoint is anomalous or no further datapoints could be generated, then
				# then False is returned
				# Otherwise a list of lists, each sublist corresponding to a generated datapoint, is returned, where
				# the first datapoint is the normal datapoint
				results = self.generate_new_datapoint_set()

				# If generation error occurs, run diagnostic
				if results==None:
					error_count += 1
					self.run_diagnostic()
					continue

				# If generation is otherwise unsuccessful, simply move on to next iteration and try again
				if results==False:
					continue

				# Write normal datapoint
				f.write(",".join(results[0])+"\n")

				# Update counts
				normal_count+=len(results)
				anomaly_count+=len(results)-1

				# Write anomalous datapoints
				for i in range(1,len(results)):
					f.write(",".join(results[i])+"\n")

				# Provide progress updates accordingly
				if ((self.datapoint_count-normal_count)%progress_checkpoint_bar==0):
					print("Progress: {}%% complete".format(normal_count/self.datapoint_count*100))

			print("Program complete. Number of execution errors: {}".format(error_count))
			print("Normal datapoints: {}".format(normal_count))
			print("Anomalous datapoints: {}".format(anomaly_count))
		
		return

	# Compile initial list of "options"
	def initialize_options(self):

		# Get preset list of non-switch options
		self.options = copy.deepcopy(Generator_NCombined.initial_options_base)
		
		# Compile list of switches that can be closed to further increase loading percents/voltages
		# and add them to possible options
		switch_list = ["switch_{}".format(i) for i in self.switch_idxs if not self.check_if_excluded_switch(i)]
		self.options += switch_list
		
		return

	# Disconnect all loads to minimize loading percents/voltages at the start of datapoint
	# set generation
	def disable_all_loads(self):
		for i in self.options:
			if i.split("_")[0]=="switch":
				self.net.switch.at[int(i.split("_")[1]),"closed"] = False
		
		False

	# Run diagnostic if PF simulation fails - currently not implemented
	def run_diagnostic(self):
		return
	
	# Function to check if a switch is not toggleable
	# If the switch is not toggleable, True is returned
	def check_if_excluded_switch(self, idx):

		# Check if switch is already part of feeder-related "options"
		for i in Generator_NCombined.feeder_config_set.keys():
			for j in Generator_NCombined.feeder_config_set[i]["switches"]:
				if idx in j: return True
			if idx in Generator_NCombined.feeder_config_set[i]["couplers"]: return True
		
		# Check if switch is already part of transformer-related "options"
		for i in Generator_NCombined.trafo_config_set.keys():
			if idx in Generator_NCombined.trafo_config_set[i]["couplers"]: return True
		
		# Check if switch is one of the fixed switches
		if idx in Generator_NCombined.static_switch_set: return True

		return False

	# Record current grid configuration and "options" available
	def record_state(self):
		initial_state = dict()
		initial_state["switch"] = self.net["switch"].copy()
		initial_state["ext_grid"] = self.net["ext_grid"].copy()
		initial_state["trafo"] = self.net["trafo"].copy()
		initial_state["options"] = copy.deepcopy(self.options)

		return initial_state
	
	# Restore grid configuration and "options" list
	def restore_state(self,initial_state):
		self.net["switch"] = initial_state["switch"].copy()
		self.net["ext_grid"] = initial_state["ext_grid"].copy()
		self.net["trafo"] = initial_state["trafo"].copy()
		self.options = copy.deepcopy(initial_state["options"])

		return

	# while num_of_datasets < required_datasets:
	# 	state <- generate_preset_valid_state()
	# 	state <- vary_intial_load(state)
	# 	while len(options) > 0:
	# 		datapoint <- execute_random_option(options)
	# 		datapoint_after_run <- run_powerflow_simulation(datapoint)
	# 		results <- get_results(datapoint_after_run)
	# 		write_results_to_csv(results)
	# 		if anamoly in results:
	# 			break
	# 	num_of_datasets += 1

	# Generate datapoint set
	def generate_new_datapoint_set(self):

		# Clear previous power flow results
		self.clear_result()

		# Restore grid to safest configuration
		self.restore_state(self.initial_state)

		# Vary grid configuration to form normal datapoint configuration
		self.vary_initial_grid()

		# Attempt to perform power flow simulation
		try:
			pp.runpp(self.net,init='results')
		
		except:
			return None

		self.initialize_init_load()
		# Create results list, assigning results of normal datapoint as first element
		results = [self.get_result_list_modified(self.net, self.count)]
		self.count += 1

		# Check if first datapoint is anomalous - if so, exit function		
		if results[0][-2]=="1":
			self.reason.pop()
			self.count -= 1
			return False

		# Record first datapoint's configuration and remaining "options" - this will be our
		# starting point for the set's anomalous datapoints
		interm_state = self.record_state()

		datapoint = ["0"]
		# print(self.options)
		while len(self.options) > 0:
			print(self.count)
			# print(len(self.options))
			# Restore normal datapoint's configuration and "options"
			# self.restore_state(interm_state)

			# Generate a new related anomalous datapoint, getting a list if generation is
			# successful and None otherwise (eg. if power flow simulation error occurs)
			datapoint = self.generate_new_anomalous_datapoint()

			# If generation is unsuccessful or power flow simulation error occurs
			if datapoint == None:
				continue

			# Continuing adding datapoints till an anomalous result is reached.
			# datapoint.append(self.reason[self.count])
			results.append(datapoint)
			# print(datapoint)

			if datapoint[-2]=="1":
				break

		# If no anomalous datapoint was obtained return False
		if len(results)==1:
			return False

		return results

	# Vary initial grid configuration to make normal datapoint
	def vary_initial_grid(self):

		# Vary loads
		self.set_varied_loads()

		#Default Normal without disturbance: No need to run anything

		#Default Normal with disturbance: Run vary grid specific
		self.vary_grid_specific()

		# # Apply a fixed number of random "options" to make grid conditions less safe
		# for a in range(Generator_NCombined.initial_vary_count):
		# 	self.exercise_random_option()
		
		return

	# Apply random "option" to make grid conditions less safe, returning True if one was applied
	# and False otherwise
	def exercise_random_option(self):

		# If no "options" remain return False
		if len(self.options)==0:
			return False
		
		# Pop a random "option" to apply
		target = random.choice(self.options)
		self.options.remove(target)
		
		# Parse "option"
		target_params = target.split("_")
		# Apply "option"
		# In this case, for feeder "options", turn off 1 random feeder (line), then enable corresponding coupler
		# For each turned off feeder (line), open at least 1 switch in the corresponding line
		if target_params[0]=="feeder":
			enable_list = self.get_guarantee_non_extreme_list(len(Generator_NCombined.feeder_config_set[target]["switches"]))
			if "feeders" in Generator_NCombined.feeder_config_set[target]:
				for i in range(len(enable_list)):
					self.net.ext_grid.at[Generator_NCombined.feeder_config_set[target]["feeders"][i],"in_service"] = enable_list[i]
			for i in range(len(enable_list)):
				if enable_list[i]: continue
				interm_statuses = self.get_guarantee_min_1_list(len(Generator_NCombined.feeder_config_set[target]["switches"][i]),False)
				for j in range(len(interm_statuses)):
					self.net.switch.at[Generator_NCombined.feeder_config_set[target]["switches"][i][j],"closed"] = interm_statuses[j]
			for i in Generator_NCombined.feeder_config_set[target]["couplers"]:
				self.net.switch.at[i,"closed"] = True

		# In this case, for transformer "options", turn off 1 random transformer and enable corresponding output coupler
		elif target_params[0]=="trafo":
			enable_list = self.get_guarantee_non_extreme_list(len(Generator_NCombined.trafo_config_set[target]["trafos"]))
			for i in range(len(enable_list)):
				self.net.trafo.at[Generator_NCombined.trafo_config_set[target]["trafos"][i],"in_service"] = enable_list[i]
			for i in Generator_NCombined.trafo_config_set[target]["couplers"]:
				self.net.switch.at[i,"closed"] = True

		# In this case, for switch "options", simply open the switch
		else:
			self.net.switch.at[int(target_params[1]),"closed"] = False
		
		return True

	# Get a random list of boolean values of given length, that is not all True or all False
	def get_guarantee_non_extreme_list(self,length):
		pool = []
		
		for i in range(1,2**length-1):
			entry = []
			j = i

			for k in list(range(length))[::-1]:
				offset = 2**k
				if (j>=offset):
					j-=offset
					entry.append(True)
				else: entry.append(False)
			pool.append(entry)
	
		return random.choice(pool)

	# Generate new anomalous datapoint and return:
	# - list of configuration values if successful
	# - None otherwise
	def generate_new_anomalous_datapoint(self):
		
		# Clear previous power flow simulation result
		self.clear_result()
		
		# If no "options" remain, generation fails
		if not self.exercise_random_option():
			return None


		# Attempt power flow simulation
		try:
			pp.runpp(self.net,init='results')
		
		except:
			return None


		# Get results - if datapoint is still normal, recurse until an anomalous one is obtained
		# (or "options" are all exhausted or PF simulation fails)
		result = self.get_result_list_modified(self.net, self.count)
		self.count += 1
		return result
		# if result[-1]=="0":
		# 	return self.generate_new_anomalous_datapoint()
		
		# return result

	# Vary grid configuration for each datapoint
	def vary_grid_specific(self):

		# Set feeder statuses, making sure that at least 1 is on, then apply on feeders
		feeder_statuses = self.get_guarantee_min_1_list(len(self.feeder_idxs))
		for i in range(len(feeder_statuses)):
			self.net.ext_grid.at[self.feeder_idxs[i],"in_service"] = feeder_statuses[i]

		# Apply feeder statuses on corresponding line switches
		feeder_switches = [[0],[4]]
		feeder_coupler = []
		self.enforce_feeder(feeder_statuses,feeder_switches,feeder_coupler)
	
		# Set substation 1 to substation 2 feeder line and substation 2 feeder coupler statuses, then apply them
		# At least 1 feeder line from S1 to S2 must be on
		# For any offline feeders, at least 1 switch along the line must be closed? Should be at least 1 switch is open
		s2_init_statuses = self.get_guarantee_min_1_list(2)
		s2_init_switches = [[2,151],[5,152]]
		s2_init_coupler = [153]
		self.enforce_feeder(s2_init_statuses,s2_init_switches,s2_init_coupler)

		# Same as previous section, but for S1 to S3
		s3_init_statuses = self.get_guarantee_min_1_list(2)
		s3_init_switches = [[1,171],[6,172]]
		s3_init_coupler = [173]
		self.enforce_feeder(s3_init_statuses,s3_init_switches,s3_init_coupler)

		# Set first substation's transformers
		# At least 1 must be on
		s1_trafos = [0,1]
		s1_trafo_coupler = []
		self.enforce_trafo(s1_trafos,s1_trafo_coupler)

		# Set second substation's transformers and output coupler statuses, then apply them
		# At least 1 transformer must be on
		s2_trafos = [2,3]
		s2_trafo_coupler = [158]
		self.enforce_trafo(s2_trafos,s2_trafo_coupler)

		# Same but for substation 3
		s3_trafos = [4,5]
		s3_trafo_coupler = [178]
		self.enforce_trafo(s3_trafos,s3_trafo_coupler)

		# Create list of constrained switches to be excluded from being closed/opened randomly
		switch_idxs_exclude = []
		#Line Switches: 0, 4, 2, 5, 151, 152, 1, 6, 171, 172
		#Coupler Switches: 3, 10, 153, 158, 173, 178
		for i in [feeder_switches,s2_init_switches,s3_init_switches]:
			for j in i:
				for k in j:
					switch_idxs_exclude.append(k)
		for i in [feeder_coupler,s2_init_coupler,s3_init_coupler,s1_trafo_coupler,s2_trafo_coupler,s3_trafo_coupler]:
			for j in i:
				switch_idxs_exclude.append(j)

		# Include CB-100 and CB-200 in said list
		switch_idxs_exclude.append(3)
		switch_idxs_exclude.append(10)

		# Randomly open/close non-constrained switches
		for i in self.switch_idxs:
			if not i in switch_idxs_exclude:
				self.net.switch.at[i,"closed"] = random.choices([True,False])

		return

	# Open/close feeders and corresponding coupler(s) given feeder statuses
	def enforce_feeder(self,statuses,switches,couplers):
		# Leave coupler open, and close feeders, if feeders are meant to be closed
		if not (False in statuses):
			for i in switches:
				for j in i:
					self.net.switch.at[j,"closed"] = True
			for i in couplers:
				self.net.switch.at[i,"closed"] = False
		
		# Otherwise, close coupler, and for open feeders, leave at least 1 switch along the feeder line open
		else:
			for i in range(len(statuses)):
				if (statuses[i]):
					for j in switches[i]:
						self.net.switch.at[j,"closed"] = True
				else:
					interm_statuses = self.get_guarantee_min_1_list(len(switches[i]),False)
					for j in range(len(interm_statuses)):
						self.net.switch.at[switches[i][j],"closed"] = interm_statuses[j]
			for i in couplers:
				self.net.switch.at[i,"closed"] = True
		
		return

	# Set transformer statuses given a list of relevant transformers, then
	# open/close transformers and corresponding coupler(s) given said generated statuses
	def enforce_trafo(self,trafos,couplers):
		
		# Generate transformer statuses, ensuring at least 1 is in service
		trafo_statuses = self.get_guarantee_min_1_list(len(trafos))

		# Apply transformer statuses
		for i in range(len(trafos)):
			self.net.trafo.at[trafos[i],"in_service"] = trafo_statuses[i]

		# Close coupler if any transformer is down, else leave open
		for i in couplers:
			self.net.switch.at[i,"closed"] = (False in trafo_statuses)
	
		return

# Main function - perform ncombined dataset generation
def main(output_file,datapoint_count):
	m = Generator_NCombined(output_file,datapoint_count)
	m.main()

	return

if __name__ == "__main__":

	# Get dataset generation arguments
	parser = argparse.ArgumentParser(description='Generate steady-state dataset, with power simulation')
	parser.add_argument('--output-file', metavar="<input target filename>",
		help="name of output file (default: generated_ss_dataset.csv)", default="generated_ss_dataset.csv", required=False)
	parser.add_argument('--datapoint-count', metavar="<input number of datapoints>",
		help="number of normal datapoints to generate (default: 20000)", default=20000, required=False)
	
	# Parse arguments, execute generation and measure time taken
	args = parser.parse_args()
	start_time = time.time()
	main(args.output_file, int(args.datapoint_count))
	print("Execution time: {}s".format(time.time()-start_time))
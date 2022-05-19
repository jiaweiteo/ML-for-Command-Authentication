from generate_ss_datasets_common import Generator_Common
from pandapower_net import Pandapower_Net
import pandapower as pp
import copy
import random
import argparse
import time
import logging
import math
import shap

##### Attack Dataset generator
##### Generates all possible unique combinations of a grid
##### We are only considering switches along feeder lines, transformers and the circuit breakers between them.
##### Total permuation = 2^18=262144 different permutations for a unique configuration.
class Generator_attack_config(Generator_Common):

	# List of default non-switch options (to push datapoint towards anomalous results)
	initial_options_base = ["feeder_0","feeder_1","feeder_2","trafo_0","trafo_1","trafo_2"]

	# Dictionary of elements to alter for initial feeder options
	feeder_config_set = {
		"feeder_0": {
			"feeders": [0,1],
			"switches": [[0],[4]],
			"couplers": [3]
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
			"couplers": [10]
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
	def __init__(self,output_file):
		super().__init__(output_file, 4096*25)
		# self.error_point_factor = error_point_factor

		return

	# Setup logger
	def setup_log(self):
		logging.basicConfig(filename='pandapower_log.log', level=logging.INFO)
		self.logger = logging.getLogger('generate_ss_datasets_special.py')

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
		
		# # Compile list of possible "options" (choices to push grid towards more anomalous state)
		self.initialize_options()

		# Turn off all loads (to emulate grid's safest state)
		# self.disable_all_loads()


		# Generate Unique Permutations
		SS_1, SS_2, SS_3, SS1_Switches, SS2_Switches, SS3_Switches = self.generate_permutations()

		# Record the current grid configuration and available "options" list - this is to reset
		# the grid at the start of each datapoint set
		self.initial_state = self.record_state()

		with open(self.output_file,"w") as f:
			# print(SS3_Switches)
			# Compile and write headers for CSV values
			headers = self.compile_headers()
			f.write(",".join(headers)+"\n")

			# Initialize counts for normal datapoints, generation failures and anomalous datapoints respectively
			normal_count = 0
			error_count = 0
			anomaly_count = 0

			count = 0
			# Define thresholds for number of normal datapoints to be generated, after each occurrence of which
			# a progress update will be shown in console
			progress_checkpoint_bar = self.datapoint_count//10

			count = 0
			#Generate unique starting configurations
			for i in range(0, len(SS_1)):
				for j in range(0, len(SS_2)):
					for k in range(0, len(SS_3)):

						self.clear_result()
						self.restore_state(self.initial_state)
						
						SS1_perm = SS_1[i]
						SS2_perm = SS_2[j]
						SS3_perm = SS_3[k]
						
						#Generated 1 unique configuration
						self.generate_attack_config(SS1_perm, SS2_perm, SS3_perm, SS1_Switches, SS2_Switches, SS3_Switches)

						self.config_state = self.record_state()

						#Vary Load Profile
						#Load 1 = 0-40%, Load 2=40-60%, Load 3=60-80%, Load 4=80-100%, Load 5=100-130%, Load 6=130-150%
						# load_profiles = [[0,40], [40,70], [70,100], [100,120], [120,150]]
						# for load_profile in load_profiles:
						# 	self.clear_result()
						# 	self.restore_state(self.config_state)

						# 	self.vary_load_profile(self.load_idxs, self.original_loads, self.net, load_profile)

						# 	# print(self.net)
						# 	#Vary options/Circuit Breaker opening
						# 	for i in range(0,self.initial_vary_count):
						# 		self.exercise_random_option()
									
						# 		count += 1
						# 		# print("Datapoint: " + str(count))

						# Attempt to perform power flow simulation
						try:
							pp.runpp(self.net,init='results')
						
						except Exception as E:
							print("Datapoint: " + str(count))
							print(E)
							error_count += 1
							print(error_count)
							continue

						self.initialize_init_load()


						# Create results list, assigning results of normal datapoint as first element
						results = self.get_result_list_modified(self.net, count)
						count += 1
						print("Datapoint :" + str(count))

						# Write normal datapoint
						f.write(",".join(results)+"\n")

						# Update counts
						normal_count+=1

						# Provide progress updates accordingly
						if ((self.datapoint_count-normal_count)%progress_checkpoint_bar==0):
							print("Progress: {}%% complete".format(normal_count/self.datapoint_count*100))

						# Check if first datapoint is anomalous - if so, exit loop		
						if results[-1]=="1":
							anomaly_count += 1
							# break


							

			print("Program complete. Number of execution errors: {}".format(error_count))
			print("Normal datapoints: {}".format(normal_count))
			print("Anomalous datapoints: {}".format(anomaly_count))
			
			return

	# Compile initial list of "options"
	def initialize_options(self):

		# Get preset list of non-switch options
		self.options = copy.deepcopy(Generator_attack_config.initial_options_base)
		
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
		for i in Generator_attack_config.feeder_config_set.keys():
			for j in Generator_attack_config.feeder_config_set[i]["switches"]:
				if idx in j: return True
			if idx in Generator_attack_config.feeder_config_set[i]["couplers"]: return True
		
		# Check if switch is already part of transformer-related "options"
		for i in Generator_attack_config.trafo_config_set.keys():
			if idx in Generator_attack_config.trafo_config_set[i]["couplers"]: return True
		
		# Check if switch is one of the fixed switches
		if idx in Generator_attack_config.static_switch_set: return True

		return False

	# Record current grid configuration and "options" available
	def record_state(self):
		initial_state = dict()
		initial_state["switch"] = self.net["switch"].copy()
		initial_state["ext_grid"] = self.net["ext_grid"].copy()
		initial_state["trafo"] = self.net["trafo"].copy()
		initial_state["options"] = copy.deepcopy(self.options)
		# print(initial_state)
		return initial_state
	
	# Restore grid configuration and "options" list
	def restore_state(self,initial_state):
		self.net["switch"] = initial_state["switch"].copy()
		self.net["ext_grid"] = initial_state["ext_grid"].copy()
		self.net["trafo"] = initial_state["trafo"].copy()
		self.options = copy.deepcopy(initial_state["options"])

		return

	# Vary grid configuration for each datapoint
	# Generate 4096 Unique Combinations
	def generate_permutations(self):
	# def vary_grid_specific(self):

		permutations_invalid = [[False, False, False],
						[False, False, True],
						[False, True, False],
						[True, False, False]]

		permutations_valid = [[True, True, True],
						[True, True, False],
						[True, False, True],
						[False, True, True]]

		permutations = permutations_valid + permutations_invalid
		print(permutations)

		SS1 = [] 
		SS1_Switches = [[0],[4],[3],[0],[1],[10]]
		# Unique permutations for SS-1:
		for i in range(len(permutations)):
			#CB0,CB4,CB3
			feeder_SS1 = permutations[i]
			for j in range(len(permutations)):
				#T0,T1,CB0
				trafos_SS1 = permutations[j]
				SS1.append(feeder_SS1 + trafos_SS1)
		
		SS2 = []
		SS2_Switches = [[2,151],[5,152],[153],[2],[3],[158]]
		# Unique permutations for SS-2:
		for i in range(len(permutations)):
			#CB0,CB4,CB3
			feeder_SS2 = permutations[i]
			for j in range(len(permutations)):
				#T0,T1,CB0
				trafos_SS2 = permutations[j]
				SS2.append(feeder_SS2 + trafos_SS2)

		SS3 = []
		SS3_Switches = [[1,171],[6,172],[173],[4],[5],[178]]
		# Unique permutations for SS-3:
		for i in range(len(permutations)):
			#CB0,CB4,CB3
			feeder_SS3 = permutations[i]
			for j in range(len(permutations)):
				#T0,T1,CB0
				trafos_SS3 = permutations[j]
				SS3.append(feeder_SS3 + trafos_SS3)

		return (SS1, SS2,SS3, SS1_Switches, SS2_Switches, SS3_Switches)
	
	#Create 1 instance of a unique grid configuration
	def generate_attack_config(self, SS1_perm, SS2_perm, SS3_perm, SS1_Switches, SS2_Switches, SS3_Switches):
		for l in range(0,6):
			m=0
			# SS1_Switches = [[0],[4],[3],[0],[1],[10]]
			for m in range(0,len(SS1_Switches[l])):
				# if l < 2:
					# self.net.ext_grid.at[self.feeder_idxs[l],"in_service"] = SS1_perm[l]

				if l < 3 or l == 5: #Feeder/CB switches
					self.net.switch.at[SS1_Switches[l][m], "closed"] = SS1_perm[l]
					
				else: #Trafos switches
					self.net.trafo.at[SS1_Switches[l][m], "in_service"] = SS1_perm[l]
			m=0
			# SS2_Switches = [[2,151],[5,152],[153],[2],[3],[158]]
			for m in range(0,len(SS2_Switches[l])):
				if l < 3 or l == 5: #Feeder/CB switches
					self.net.switch.at[SS2_Switches[l][m], "closed"] = SS2_perm[l]
				else:
					self.net.trafo.at[SS2_Switches[l][m], "in_service"] = SS2_perm[l]
			m=0	
			# SS3_Switches = [[1,171],[6,172],[173],[4],[5],[178]]
			for m in range(0,len(SS3_Switches[l])):
				if l < 3 or l == 5: #Feeder/CB switches
					self.net.switch.at[SS3_Switches[l][m], "closed"] = SS3_perm[l]
					# print(self.net.switch.at[173, "closed"])
				else:
					self.net.trafo.at[SS3_Switches[l][m], "in_service"] = SS3_perm[l]

		return

	# Vary grid loads for current datapoint
	def vary_load_profile(self, load_idxs,original_loads,net,load_profile):
		for i in load_idxs:
			# Select random percentage between the lower and upper limits defined in load_variance_limits
			load_factor = random.uniform(load_profile[0],load_profile[1])/100
			net.load.at[i,"p_mw"] = original_loads.at[i,"p_mw"]*load_factor
			net.load.at[i,"q_mvar"] = original_loads.at[i,"q_mvar"]*load_factor
		
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
			enable_list = self.get_guarantee_non_extreme_list(len(Generator_attack_config.feeder_config_set[target]["switches"]))
			if "feeders" in Generator_attack_config.feeder_config_set[target]:
				for i in range(len(enable_list)):
					self.net.ext_grid.at[Generator_attack_config.feeder_config_set[target]["feeders"][i],"in_service"] = enable_list[i]
			for i in range(len(enable_list)):
				if enable_list[i]: continue
				interm_statuses = self.get_guarantee_min_1_list(len(Generator_attack_config.feeder_config_set[target]["switches"][i]),False)
				for j in range(len(interm_statuses)):
					self.net.switch.at[Generator_attack_config.feeder_config_set[target]["switches"][i][j],"closed"] = interm_statuses[j]
			for i in Generator_attack_config.feeder_config_set[target]["couplers"]:
				self.net.switch.at[i,"closed"] = True

		# In this case, for transformer "options", turn off 1 random transformer and enable corresponding output coupler
		elif target_params[0]=="trafo":
			enable_list = self.get_guarantee_non_extreme_list(len(Generator_attack_config.trafo_config_set[target]["trafos"]))
			for i in range(len(enable_list)):
				self.net.trafo.at[Generator_attack_config.trafo_config_set[target]["trafos"][i],"in_service"] = enable_list[i]
			for i in Generator_attack_config.trafo_config_set[target]["couplers"]:
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

# Main function - perform special dataset generation
def main(output_file):
	m = Generator_attack_config(output_file)
	m.main()

	return

if __name__ == "__main__":

	# Get dataset generation arguments
	parser = argparse.ArgumentParser(description='Generate steady-state dataset, with power simulation')
	parser.add_argument('--output-file', metavar="<input target filename>",
		help="name of output file (default: generated_ss_dataset.csv)", default="generated_ss_dataset.csv", required=False)
	# parser.add_argument('--datapoint-count', metavar="<input number of datapoints>",
	# 	help="number of normal datapoints to generate (default: 200)", default=200, required=False)
	# parser.add_argument('--error-point-factor', metavar="<input error point factor>",
	# 	help="maximum number of anomalous datapoints to generate for each normal datapoint (default: 5)", default=5, required=False)
	
	# Parse arguments, execute generation and measure time taken
	args = parser.parse_args()
	start_time = time.time()
	main(args.output_file)
	print("Execution time: {}s".format(time.time()-start_time))

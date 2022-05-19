import random
import argparse
import logging
import time
import pandapower as pp
from generate_ss_datasets_common import Generator_Common

##### Constrained dataset generator
##### This generator ensures that for each substation, at least 1 transformer/feeder is online and connected,
##### and that couplers be activated if needed (except for CB-100 and CB-200 which are always closed)
##### such that all loads are connected unless their respective switches are open
##### All other (so called non-constrained) switches are closed/opened randomly
##### Constrained Switches:
##### Line Switches: 0, 4, 2, 5, 151, 152, 1, 6, 171, 172
##### Coupler Switches: 3, 10, 153, 158, 173, 178
class Generator_Constrained(Generator_Common):

	# For initialization, define probability that a non-constrained switch is closed
	def __init__(self,output_file, datapoint_count,switch_close_chance):
		super().__init__(output_file, datapoint_count)
		self.switch_close_chance = switch_close_chance
		self.count = -1 #For unconstrained/constrained

		return
	
	# Define logger
	def setup_log(self):
		logging.basicConfig(filename='pandapower_log.log', level=logging.INFO)
		self.logger = logging.getLogger('generate_ss_datasets_constrained.py')

		return

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
				self.net.switch.at[i,"closed"] = random.choices([True,False],weights=[self.switch_close_chance,1-self.switch_close_chance])[0]

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

	# Run diagnostic for any generation failures
	# Currently no action is being done
	def run_diagnostic(self):
		
		return

# Main function: perform constrained dataset generation
def main(output_file,datapoint_count,switch_close_chance):
	m = Generator_Constrained(output_file,datapoint_count,switch_close_chance)
	m.main()

	return

# To be executed if this script is run as a python script instead of imported
if __name__ == "__main__":

	# Get arguments for running script
	parser = argparse.ArgumentParser(description='Generate steady-state dataset, with power simulation')
	parser.add_argument('--output-file', metavar="<input target filename>",
		help="name of output file (default: generated_ss_dataset.csv)", default="generated_ss_dataset.csv", required=False)
	parser.add_argument('--datapoint-count', metavar="<input number of datapoints>",
		help="number of datapoints to generate (default: 20000)", default=20000, required=False)
	parser.add_argument('--switch-close-chance', metavar="<input load switch closing chance>",
		help="probability that an unconstrained load switch is closed (default: 0.5)", default=0.5, required=False)

	# Parse arguments
	args = parser.parse_args()

	# Pass arguments for generation and measure generation time
	start_time = time.time()
	main(args.output_file, int(args.datapoint_count),float(args.switch_close_chance))
	print("Execution time: {}s".format(time.time()-start_time))

import pandapower as pp
import random
import argparse
import logging
import time
from generate_ss_datasets_common import Generator_Common

##### Unconstrained dataset generator:
##### In this generator, switches, transformers and feeders are all toggled randomly
##### with equal probability of opening/closing
class Generator_Unconstrained(Generator_Common):
	
	# For initialization, define probability that a non-constrained switch is closed
	def __init__(self,output_file, datapoint_count):
		super().__init__(output_file, datapoint_count)
		self.count = -1 #For unconstrained/constrained

		return


	# Setup logger
	def setup_log(self):
		logging.basicConfig(filename='pandapower_log.log', level=logging.INFO)
		self.logger = logging.getLogger('generate_ss_datasets_unconstrained.py')

		return
	
	# Randomly toggle switches, transformers and feeders
	def vary_grid_specific(self):
		for i in self.switch_idxs:
			self.net.switch.at[i,"closed"] = random.choice([True,False])

		for i in self.trafo_idxs:
			self.net.trafo.at[i,"in_service"] = random.choice([True,False])
	
		feeders_in_service = self.get_guarantee_min_1_list(len(self.feeder_idxs))
		# print(feeders_in_service)
		for i in range(len(self.feeder_idxs)):
			self.net.ext_grid.at[self.feeder_idxs[i],"in_service"] = feeders_in_service[i]

		return

	# Run diagnostic if PF simulation fails - currently unimplemented
	def run_diagnostic(self):
		
		return		

# Main function - perform unconstrained dataset generation
def main(output_file,datapoint_count):
	m = Generator_Unconstrained(output_file,datapoint_count)
	m.main()

	return

# Executed if script is run as Python script instead of imported
if __name__ == "__main__":

	# Get generation arguments
	parser = argparse.ArgumentParser(description='Generate steady-state dataset, with power simulation')
	parser.add_argument('--output-file', metavar="<input target filename>",
		help="name of output file (default: generated_ss_dataset.csv)", default="generated_ss_dataset.csv", required=False)
	parser.add_argument('--datapoint-count', metavar="<input number of datapoints>",
		help="number of datapoints to generate (default: 20000)", default=20000, required=False)

	# Parse arguments, perform generation and record time taken
	args = parser.parse_args()
	start_time = time.time()
	main(args.output_file, int(args.datapoint_count))
	print("Execution time: {}s".format(time.time()-start_time))

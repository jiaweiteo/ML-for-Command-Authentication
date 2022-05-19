import argparse
import time
import pandas as pd
import sklearn
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, AdaBoostClassifier
import xgboost as xgb
from sklearn.model_selection import GridSearchCV
from sklearn.neural_network import MLPClassifier
from joblib import dump
import sys
import numpy as np
np.random.seed(5)


# Main function: perform model grid search
# Run this file at ./ml_models Directory, NOT "Midterm Progress" directory
def main():
	print('The scikit-learn version is {}.'.format(sklearn.__version__))
	print(sys.version)
	trainingfiles = [
		"../datasets/Training/constrained.csv", 
		"../datasets/Training/ncombined.csv", 
		"../datasets/Training/unique_normal.csv", 
		"../datasets/Training/unor.csv"
		]
	testingfiles = [
		"../datasets/Testing/unconstrained.csv", 
		"../datasets/Testing/attack.csv", 
		"../datasets/Testing/special.csv",
		]

	with open('sklearn_results_final.txt', 'w') as f:

		for testing_data in testingfiles:
			#Get testing dataset
			test_df = pd.read_csv(testing_data)
			test_df.fillna(0,inplace=True)

			# Get features
			X_test = test_df.drop(columns=['anomaly', 'reason'])

			# Get labels
			y_test = test_df['anomaly']	

			for training_data in trainingfiles:
				# Get training dataset
				df = pd.read_csv(training_data)
				df.fillna(0,inplace=True)

				# Get features
				X_train = df.drop(columns=['anomaly', 'reason'])


				# Get labels
				y_train = df['anomaly']		

				# Determine ML model family to use and grid search parameters, depending on algorithm specified
				classifier = None
				parameters = None
				models = [
					# "SVM", 
					"XGB", 
					"RF", 
					"LogisticRegression", 
					"Adaboost", 
					"DT"
					]

				for model in models:
					test = ("Testing: " + testing_data + " Training: " + training_data + " Model: " + model)
					print(test)
					f.write(test + "\n")
					if model==None or model=="SVM":
						best_params = {
							'kernel' : 'sigmoid'
						}
						clf = SVC(**best_params)
						parameters = {
							'kernel': ['linear', 'poly', 'rbf', 'sigmoid']
						}
					elif model=="XGB":
						best_params = {'colsample_bytree': 0.5,
						'gamma': 2,
						'learning_rate': 0.5,
						'max_depth': 15,
						'reg_lambda': 1,
						'scale_pos_weight': 1,
						'subsample': 0.8
						}		
						clf = xgb.XGBClassifier(**best_params, objective="binary:logistic", seed=42)
						parameters = {
							'n_estimators': [100, 200, 300, 400, 500],
							'max_depth': [1,2,3],
							'learning_rate': [0.01,0.1,1],
							'random_state': [42]}
					elif model=="RF":
						best_params = {
							'n_estimators': 300,
							'max_depth': 10,
							'max_features': 'auto'
						}
						clf = RandomForestClassifier(**best_params)
						parameters = {
							'n_estimators': [100, 200, 300, 400, 500],
							'max_depth': [2,4,6],
							'max_features': ['auto','log2']
						}
					elif model=="LogisticRegression":
						best_params = {
							'solver': "lbfgs",
							'tol': 1e-5,
							'max_iter': 200
						}		
						clf = LogisticRegression(**best_params)
						parameters = {
							'solver': ['newton-cg','lbfgs','sag','saga'],
							'tol': [1e-5,1e-4,1e-3],
							'max_iter': [100,200,300]
						}
					elif model=="LinearRegression":
						clf = LinearRegression()
						parameters = {
							'normalize': [False,True]
						}
					elif model=="Adaboost":
						best_params = {
							'n_estimators': 300,
							'learning_rate': 0.1,
						}		
						clf = AdaBoostClassifier(**best_params)
						parameters = {
							'n_estimators': [100, 200, 300, 400, 500],
							'learning_rate': [0.01,0.1,1]
						}
					elif model=="MLP":
						clf = MLPClassifier()
						parameters = {
							'activation': ['logistic','tanh','relu'],
							'learning_rate': ['constant','invscaling','adaptive'],
							'learning_rate_init': [0.001,0.01],
							'hidden_layer_sizes': [(128,256,64),(128,256,128,64)]
						}
					elif model=="DT":
						best_params = {
							'min_samples_leaf': 1,
							'max_depth': 8,
							'max_features': 'auto'
						}		
						clf = DecisionTreeClassifier(**best_params)
						parameters = {
							'min_samples_leaf': [1,2,3],
							'max_depth': [2,4,6],
							'max_features': ['auto','log2']
						}
					else:
						print("Invalid model specified! Exiting...")
						return

					# Define grid search object
					# Note that by default, 5-fold cross validation is performed during grid search
					# clf = GridSearchCV(classifier, param_grid=parameters)

					# print(clf)
					# Perform grid search
					clf.fit(X_train,y_train)

					# Save grid search object with best model
					# s = dump(clf,output_file)

					# Print found best parameters and best accuracy
					# print("Best params: ",clf.best_params_)
					# print("Accuracy: ",clf.best_score_)

					preds = clf.predict(X_test)			
					print(preds)
					print(np.random.get_state()[1][0])

					
					# Calculate and print statistics
					TN, TP, FN, FP = 0, 0, 0, 0
					TP_list = []
					TN_list = []
					FN_list = []
					FP_list = []
					# print(y_test)
					# y_test = y_test.values.tolist()
					for i in range(len(y_test)):
						if y_test[i]==0:
							if preds[i]==0: 
								TN += 1
								TN_list.append(i)
							else: 
								FP += 1
								FP_list.append(i)
						else:
							if preds[i]==0: 
								FN += 1
								FN_list.append(i)
							else: 
								TP += 1
								TP_list.append(i)

					result = ("TN", TN, "TP", TP, "FN", FN, "FP", FP)
					print(result)
					f.write(' '.join(str(s) for s in result) + " ")
					f.write("\n")
					# f.write(result + "\n")
					# accuracy = "Accuracy: {}%".format((TN+TP)*100/(TN+TP+FN+FP))
					# f.write(accuracy + "\n")

					#  Calculate and print precision, recall and F1 score
					precision = 0 if TP+FP==0 else TP/(TP+FP)
					recall = 0 if TP+FP==0 else TP/(TP+FN)
					fscore = 0 if precision+recall==0 else 2*precision*recall/(precision+recall)

					stats = "Overall statistics: Accuracy: {}% Precision: {} Recall: {} F1 Score: {}".format((TN+TP)*100/(TN+TP+FN+FP), precision, recall, fscore)
					print(stats)
					f.write(stats + "\n")
					f.write("\n")



# To be executed if run as Python script and not as imported module
if __name__ == "__main__":

	# Get arguments
	# parser = argparse.ArgumentParser(description='Generate training model to detect anomalous would-be states')
	# parser.add_argument('--input-file', metavar="<input training data filename>",
	# 	help="name of training data filename (default: generated_ss_dataset.csv)", default="generated_ss_dataset.csv", required=False)
	# parser.add_argument('--output-file', metavar="<input target filename>",
	# 	help="name of output file (default: ml_model.joblib)", default="ml_model.joblib", required=False)
	# parser.add_argument('--model', metavar='<input model type>',
	# 	help="ML model to use [SVM/GBT/RF/LogisticRegression/LinearRegression/AdaBoost/MLP] (default: SVM)", default=None, required=False)
	
	# Parse arguments, run grid search and measure grid search time
	# args = parser.parse_args()
	start_time = time.time()
	# main(args.input_file, args.output_file, args.model)
	main()
	print("Execution time: {}s".format(time.time()-start_time))
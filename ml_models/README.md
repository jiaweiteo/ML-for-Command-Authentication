# ml_models: Folder for ML models Implementation and Results

## Directory Structure

- sk_experiments.py: script for grid search, training and testing of scikit-learn models
- tf_model_ann.ipynb: script for grid search, training and testing of ANN models
- xgboost.ipynb: script for grid search, training and testing of XGBoost model
- sklearn_results_final.txt: Results of sklearn models trained and tested against different datasets
- xgboost_features_importance.pdf: Bar chart describing the importance of each feature in dataset

### Scikit-learn based machine learning

#### Grid search, Training and Testing (sk_experiments.py)

At the most basic level, simply run

    python sk_experiments.py

The python file contains several ML models, namely: XGB, RF, LogisticRegression, LinearRegression, AdaBoost, MLP, DT. Modification of parameters, ML models, training and testing datasets is done by editing the code.

**(Currently commented out)** This script has several flags that can be customized:

- --input-file &lt;name of training dataset>: name of CSV training dataset to be used (default: generated_ss_dataset.csv)
- --output-file &lt;name of output ML model>: name for output file containing grid search object with corresponding best model produced from grid search (default: ml_model.joblib)
- --model &lt;algorithm name>: name of algorithm to use for machine learning models for grid search (default: SVM); currently available options are: XGB,RF,LogisticRegression,LinearRegression,AdaBoost,MLP,DT

For example, to train a GBT model and save it as nano.joblib run

    python sk_experiments_train.py --output-file nano.joblib --model GBT

After entering the command, the console will not show any output until grid search is completed. This is normal. Once it is completed you will see something like this:

![Scikit-learn grid search complete](../readme_img/sk_gs_complete.png)

#### XGBoost Grid search, training and testing (xgboost.ipynb)

Simply execute the cells in sequential order. Grid search comes first, followed by training the XGBoost model with a selected training dataset and lastly testing it with a selected dataset. Tuning of hyperparameters of the XGBoost model can be done manually by editing the source code. This should not be needed if grid search is performed instead. However, grid search can take a fairly large amount of time (>1 day) depending on the number of varying parameters. The training and testing dataset selected is also modified in the source code.

There are also some preliminary source code evaluating the features importance at the end of the file.

### TensorFlow-based machine learning

#### Grid search, Training and Testing (tf_model_ann.ipynb)

Similar to xgboost.ipynb, to run the Jupyter notebook, simply execute the cells in sequential order. Grid search comes first, followed by training the ANN model with a selected training dataset and lastly testing it with a selected testing dataset. Tuning of hyperparameters of the ANN model can be done manually by editing the source code. This should not be needed if grid search is performed instead. However, grid search can take a fairly large amount of time (>1 day) depending on the number of varying parameters. The training and testing dataset selected is also modified in the source code.

Additionally, there are some preliminary source code toying with the idea of adding more cost to false negatives and balancing the imbalanced data.
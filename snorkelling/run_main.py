import sys
sys.path.append('../')
from snorkelling.labelling_functions import get_lfs
from snorkel.labeling import PandasLFApplier
from snorkel.labeling import LFAnalysis
import pandas as pd
import numpy as np

ABSTAIN = -1
CALL = 1
NOTCALL = 0


def run_main(train_pkl: str = None, test_pkl: str = None, ground_truth: bool = True,  excluded_lfs: list = [], train_pd: pd.DataFrame = None, test_pd: pd.DataFrame = None, options: dict = {}):
    '''Generate the snorkel classifier and return its accuracy and the label matrix
    
    Options: [create_label_column, ground_truth, excluded_lfs]
    '''
    if train_pkl == None:
        train: pd.DataFrame = train_pd
    else: 
        train: pd.DataFrame = pd.read_pickle(train_pkl)
    if test_pkl == None:
        test: pd.DataFrame = test_pd
    else:
        test: pd.DataFrame = pd.read_pickle(test_pkl)
    if options.get('create_label_column', True):
        def create_label_column(df: pd.DataFrame):
            df = df.copy(deep=True)
            # df["label"] = df["Answer_is-a-call_most"].apply(lambda x: CALL if x else NOTCALL)
            df["label"] = df["Answer_is-a-call_most"].apply(lambda x: CALL if x else NOTCALL)
            # # drop redundant columns
            # data_pd = data_pd.drop(columns=["Answer_is-a-call_most", "Answer_is-a-call_some", "Answer_is-a-call_none", "Input_video_id", "Answer_is-a-call_none_y"])
            return df
        train = create_label_column(train)
        test = create_label_column(test)

    lfs = get_lfs()
    lf_array = []
    for lf in lfs.keys():
        lf_array += lfs[lf]
    #lf_array = lfs['general'] + lfs['scam_types'] + lfs['transcript']
    lf_array = list(filter(lambda x: x.name not in options.get('excluded_lfs', []), lf_array))

    applier = PandasLFApplier(lfs=lf_array)
    L_train = applier.apply(df=train)
    L_test = applier.apply(df=test)

    from snorkel.labeling.model import LabelModel
    label_model = LabelModel(cardinality=2)
    if options.get('ground_truth', True):
        print("Ground Truth provided")
        label_model.fit(L_train=L_train, Y_dev=train['label'].values, n_epochs=500, log_freq=1000, seed=123)
    else:
        print("Ground Truth not provided")
        label_model.fit(L_train=L_train, n_epochs=500, log_freq=1000, seed=123)

    label_model_acc = label_model.score(L=L_test, Y=test.label.values, tie_break_policy="random", metrics=["accuracy", "coverage", "precision", "recall", "f1"])
    labelled_test = label_model.predict(L=L_test, tie_break_policy="random")
    return label_model_acc, labelled_test

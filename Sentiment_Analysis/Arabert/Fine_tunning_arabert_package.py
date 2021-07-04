# !pip install optuna==2.3.0
# !pip install transformers==4.2.1
# !pip install farasapy
# !pip install pyarabic
# !git clone https://github.com/aub-mind/arabert

from arabert.preprocess import ArabertPreprocessor
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, f1_score, confusion_matrix, precision_score , recall_score

from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer, BertTokenizer
from transformers.data.processors import SingleSentenceClassificationProcessor
from transformers import Trainer , TrainingArguments
from transformers.trainer_utils import EvaluationStrategy
from transformers.data.processors.utils import InputFeatures
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
from sklearn.utils import resample
import logging
import torch
import optuna

# (1)load libraries 
import json, sys, regex
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from keras.preprocessing.sequence import pad_sequences
from sklearn.model_selection import train_test_split
from tqdm import tqdm, trange
import pandas as pd
import os
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, recall_score, precision_score, classification_report, confusion_matrix
##----------------------------------------------------
import pandas as pd
import numpy as np

from tqdm import tqdm_notebook as tqdm
from sklearn.model_selection import train_test_split
##------------------------------------------------------
import re


_DEFAULT_LABELS=[0,1,2]


class Dataset:
    def __init__(
        self,
        name,
        train,
        test,
        label_list,
    ):
        self.name = name
        self.train = train
        self.test = test
        self.label_list = label_list

class BERTDataset(Dataset):
    def __init__(self, text, target, model_name, max_len, label_map):
      super(BERTDataset).__init__()
      self.text = text
      self.target = target
      self.tokenizer_name = model_name
      self.tokenizer = AutoTokenizer.from_pretrained(model_name)
      self.max_len = max_len
      self.label_map = label_map
      

    def __len__(self):
      return len(self.text)

    def __getitem__(self,item):
      text = str(self.text[item])
      text = " ".join(text.split())


        
      input_ids = self.tokenizer.encode(
          text,
          add_special_tokens=True,
          max_length=self.max_len,
          truncation='longest_first'
      )     
    
      attention_mask = [1] * len(input_ids)

      # Zero-pad up to the sequence length.
      padding_length = self.max_len - len(input_ids)
      input_ids = input_ids + ([self.tokenizer.pad_token_id] * padding_length)
      attention_mask = attention_mask + ([0] * padding_length)    
      
      return InputFeatures(input_ids=input_ids, attention_mask=attention_mask, label=self.label_map[self.target[item]])

class BERTDatasetTest(Dataset):
    def __init__(self, text, model_name, max_len, label_map):
      super(BERTDataset).__init__()
      self.text = text
      self.tokenizer_name = model_name
      self.tokenizer = AutoTokenizer.from_pretrained(model_name)
      self.max_len = max_len
      self.label_map = label_map
      

    def __len__(self):
      return len(self.text)

    def __getitem__(self,item):
      text = str(self.text[item])
      text = " ".join(text.split())


        
      input_ids = self.tokenizer.encode(
          text,
          add_special_tokens=True,
          max_length=self.max_len,
          truncation='longest_first'
      )     
    
      attention_mask = [1] * len(input_ids)

      # Zero-pad up to the sequence length.
      padding_length = self.max_len - len(input_ids)
      input_ids = input_ids + ([self.tokenizer.pad_token_id] * padding_length)
      attention_mask = attention_mask + ([0] * padding_length)    
      
      return InputFeatures(input_ids=input_ids, attention_mask=attention_mask)

# MODEL_PATH_BEGIN_FINETUNE='/content/MARBERT_pytorch_verison'

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print ("your device ", device)

class SentimentIdentificationArabert(object):
  """A class for finetunning, evaluating and running the sentiment classification on MARBERT model
     After initializing an instance, you must
    run the train method once before using it.
    Args:
        labels (:obj:`set` of :obj:`str`, optional): The set of sentiment labels
            used in the training data in the main model.
            If None, the default labels are used.
            Defaults to None.

        max_seq_length (:obj:`int`, optional): maximum sequence length for the model
            
            If None, the default max_seq_length are used.
            Defaults to 256 .

        num_epoch (:obj:`int`, optional): number of epoch used for training the model
            
            If None, the default num_epoch are used.
            Defaults to 3 .

        batch_size (:obj:`int`, optional):batch size used for training the model            
            If None, the default batch_size are used.
            Defaults to 16 .

        lr (:obj:`int`, optional):initial learning rate used for training the model            
            If None, the default lr are used.
            Defaults to 5e-5 .
        
       
    """
  def __init__(self, labels=None,max_seq_length=256,num_epoch=3,batch_size=16,lr=5e-5
                 ):
        if labels is None:
            self.labels = _DEFAULT_LABELS
        self._labels_sorted = sorted(self.labels)
        self._is_trained = False
        self.model_name='aubmindlab/bert-base-arabertv02'
        self.task='classification'
        self.num_epoch=num_epoch
        self.batch_size=batch_size
        self.max_seq_length=max_seq_length
        self.lr=lr
        self.__arabert_prep = ArabertPreprocessor(self.model_name.split("/")[-1])
  def create_label2ind_file(self):

    self.label_map = { v:index for index, v in enumerate(self._labels_sorted) }

  def save_label2ind_file(self,path):
    """Save  the label 2 indexr on a given data set.
      Args:
          Path (:obj:`str`): Path where you want to save the feature vector .
              
          
      """
    with open(path, 'w') as json_file:
        json.dump(self.label_map, json_file)

  def data_prepare_BERT(self,X_train,y_train):
    X_train = X_train.apply(self.__arabert_prep.preprocess)

    train_dataset = BERTDataset(X_train.to_list(),y_train.to_list(),self.model_name,self.max_seq_length,self.label_map)
    
      
    return train_dataset
  def data_prepare_BERT_test(self,X_test):
    X_test = X_test.apply(self.__arabert_prep.preprocess)

    test_dataset = BERTDatasetTest(X_test.to_list(),self.model_name,self.max_seq_length,self.label_map)
    
    return test_dataset

  def model_init(self):
    return AutoModelForSequenceClassification.from_pretrained(self.model_name, return_dict=True, num_labels=len(self.label_map))
  
  def compute_metrics(self,p):

    #p should be of type EvalPrediction

    preds = np.argmax(p.predictions, axis=1)
    assert len(preds) == len(p.label_ids)
    #print(classification_report(p.label_ids,preds))
    #print(confusion_matrix(p.label_ids,preds))

    macro_f1_pos_neg = f1_score(p.label_ids,preds,average='macro',labels=[0,1])
    macro_f1 = f1_score(p.label_ids,preds,average='macro')
    macro_precision = precision_score(p.label_ids,preds,average='macro')
    macro_recall = recall_score(p.label_ids,preds,average='macro')
    acc = accuracy_score(p.label_ids,preds)
    return {
        'macro_f1' : macro_f1,
        'macro_f1_pos_neg' : macro_f1_pos_neg,  
        'macro_precision': macro_precision,
        'macro_recall': macro_recall,
        'accuracy': acc
    }

  
  def save_model(self,path):   
    """Save  the model on a given data set.
        Args:
            Path (:obj:`str`): Path where you want to save the model.
               
           
        """
    self.trainer.save_model(path + '/')

  def eval(self,X_eval,y_eval, data_set='DEV'):

    """Evaluate the trained model on a given data set.
        Args:
            X_eval (:obj:`np array or pandas series`, optional): loaded data for evaluation.

            y_eval (:obj:`np array or pandas series`, optional): loaded labels for evaluation.

            data_set (:obj:`str`, optional): Name of the provided data set to
                use. This is ignored if data_path is not None. Can be either
                'VALIDATION' or 'TEST'. Defaults to 'VALIDATION'.

            batch_size (:obj:`int`, optional):batch size used for training the model            
            If None, the default batch_size are used.
            Defaults to 16 .
        Returns:
            :obj:`dict`: A dictionary mapping an evaluation metric to its
            computed value. The metrics used are accuracy, f1_micro, f1_macro,
            recall_micro, recall_macro, precision_micro and precision_macro.
        """
    validation_inputs = self.data_prepare_BERT(X_eval,y_eval)
    predictions=self.trainer.predict(validation_inputs)
    all_pred=np.argmax(predictions[0],axis=1)
    all_label= [self.label_map[i] for i in y_eval]    
    accuracy = accuracy_score(all_label, all_pred)
    macro_f1_pos_neg = f1_score(all_label, all_pred,average='macro',labels=[0,1])
    f1score = f1_score(all_label, all_pred, average='macro') 
    recall = recall_score(all_label, all_pred, average='macro')
    precision = precision_score(all_label, all_pred, average='macro')
    # Get scores
    scores = {
        'Sentiment': {
            'accuracy': accuracy,
            'f1_macro': f1score,
            'recall_macro': recall,
            'precision_macro':precision
        }
    }
    return scores

  def predict(self,sentences):
    """Predict the sentiment  probability scores for a given list of
        sentences.
        Args:
            sentences (:obj:`list` of :obj:`str`): The list of sentences.
            output (:obj:`str`): The output label type. Possible values are
                'postive', 'neagtive', 'neutral'.
        Returns:
            :obj:`list` of :obj:`sentIDPred`: A list of prediction results,
            each corresponding to its respective sentence.
        """
    if isinstance(sentences, str):
      sentences=pd.Series(sentences)
    validation_inputs = self.data_prepare_BERT_test(sentences)
    predictions=self.trainer.predict(validation_inputs)
    probabilities=predictions[0]
    predicted = np.argmax(predictions[0],axis=1)   
    result = collections.deque()
    convert = lambda x: x     
    for i in range(0,len(predicted)):
      for j, val in self.label_map.items():
      
        if val==predicted[i]:
          result.append(convert(SentIDPred(j, probabilities[i])))
          break

        
      
    return list(result)    
       

         

  def fine_tune(self,X_train,y_train,X_valid=None,y_valid=None):

    """ fine tune MARBERT model.
        Args:
            X_train (:obj:`np array or pandas series`, optional): loaded training data.
               
            y_train (:obj:`np array or pandas series`, optional): loaded labels for training.

            X_valid (:obj:`np array or pandas series`, optional): loaded validation data.
               
            y_valid (:obj:`np array or pandas series`, optional): loaded labels for validation.
       
        """

    self.create_label2ind_file()
    if X_valid is None and y_valid is None:
      msk = np.random.rand(len(X_train)) < 0.8
      X_valid = X_train[~msk]
      X_train = X_train[msk]
      y_valid = y_train[~msk]
      y_train = y_train[msk]
    #-------------------------------------------------------
    train_inputs = self.data_prepare_BERT(X_train,y_train)
    validation_inputs = self.data_prepare_BERT(X_valid,y_valid)
      
    #-------------------------------------------------------
    training_args = TrainingArguments("./train")
    training_args.evaluate_during_training = True
    training_args.adam_epsilon = 1e-8
    training_args.learning_rate = self.lr
    training_args.fp16 = True
    training_args.per_device_train_batch_size = self.batch_size
    training_args.per_device_eval_batch_size = self.batch_size
    training_args.gradient_accumulation_steps = 2
    training_args.num_train_epochs= self.num_epoch
    steps_per_epoch = (len(X_train)// (training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps))
    total_steps = steps_per_epoch * training_args.num_train_epochs
    
    #Warmup_ratio
    warmup_ratio = 0.1
    training_args.warmup_steps = total_steps*warmup_ratio # or you can set the warmup steps directly 

    training_args.evaluation_strategy = EvaluationStrategy.EPOCH
    # training_args.logging_steps = 200
    training_args.save_steps = 100000 #don't want to save any model, there is probably a better way to do this :)
    training_args.seed = 42
    training_args.disable_tqdm = False
    training_args.lr_scheduler_type = 'cosine'

    #-------------------------------------------------------
    self.trainer = Trainer(
    model = self.model_init(),
    args = training_args,
    train_dataset = train_inputs,
    eval_dataset=validation_inputs,
    compute_metrics=self.compute_metrics,
)

    #------------------------------------------
    self.trainer.train()
    
    #---------------------------------------------------

import collections
class SentIDPred(collections.namedtuple('SentimentPred', ['top', 'scores'])):
    """A named tuple containing sentiment ID prediction results.
    Attributes:
        top (:obj:`str`): The sentiment label with the highest score. See
            :ref:`sentimentid_labels` for a list of output labels.
        scores (:obj:`dict`): A dictionary mapping each sentiment label to it's
            computed score.
    """


"""# Testing Production code"""

df=pd.read_csv('/content/drive/MyDrive/Omdena_sentiment/Dataset/final_text.csv')

msk = np.random.rand(len(df)) < 0.7
train = df[msk]
test = df[~msk]

msk = np.random.rand(len(train)) < 0.8
train_new = train[msk]
valid = train[~msk]

labels_numeric=[0,1,2]

train_new.dropna(inplace=True)

test.dropna(inplace=True)

valid.dropna(inplace=True)

Arabert_Sentiment_Classifier=SentimentIdentificationArabert(labels_numeric,num_epoch=1)

Arabert_Sentiment_Classifier.fine_tune(train_new['final'],train_new['label'],valid['final'],valid['label'])

MODEL_PATH_='/content/drive/MyDrive/Omdena_sentiment/Saved_models/Production/Arabert'
LABEL_2_INDEX_PATH='/content/drive/MyDrive/Omdena_sentiment/Saved_models/Production/Arabert/_labels-dict.json'

Arabert_Sentiment_Classifier.save_model(MODEL_PATH_)

Arabert_Sentiment_Classifier.save_label2ind_file(LABEL_2_INDEX_PATH)

Arabert_Sentiment_Classifier.eval(test['final'],test['label'])



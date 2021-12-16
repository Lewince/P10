from azure.cognitiveservices.language.luis.authoring import LUISAuthoringClient
from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from botbuilder.ai.luis.luis_util import LuisUtil
import datetime
import json
import math
from msrest.authentication import CognitiveServicesCredentials
import random
import time

SUBSCRIPTION_KEY_ENV_NAME = "LUIS_AUTHORING_KEY"

class LuisAppCreator:

    def __init__(self, luis_authoring_key,
                 frames, 
                 entity_keys=['or_city', 'dst_city', 'str_date', 'end_date', 'budget'],
                 intent_keys = None, 
                 luis_authoring_endpoint='https://flymeluis.cognitiveservices.azure.com/'):
        self.subscription_key = luis_authoring_key
        self.frames = frames
        self.utterances = []
        self.testset = []
        self.trainset = []
        self.client = LUISAuthoringClient(
            luis_authoring_endpoint,
            CognitiveServicesCredentials(self.subscription_key),
        )
        self.entity_keys = entity_keys
        self.intent_keys = intent_keys
        self.authoring_endpoint='https://flymeluis.cognitiveservices.azure.com/'
        self.prediction_endpoint = None
        self.app_id = None

    # Unit function generating positioning dictionary for a given entity within a given utterance : 
    def get_example_label(self, statement, entity_name, value):
                statement = statement.lower()
                value = value.lower()
                return {
                    'entity_name': entity_name,
                    'start_char_index': statement.find(value),
                    'end_char_index': statement.find(value) + len(value)
                }
    # Function building the training dict from any NER data in the "Microsoft Frames Dataset" format type : 
    def build_training_dict(self, noref = False):
        training_list = []
        args_list = []
        # for each conversation : 
        for i in range(len(self.frames)):
            # For each turn : 
            for n in self.frames[i]['turns']: 
                if 'text' in n.keys():
                    text = n['text']
                    if noref : 
                        data = n['labels']['acts_without_refs']
                    else : 
                        data = n['labels']['acts']
                        name = n['labels']['name']
                    args_dict = {}
                    # Imputing zeros where no surveyrating is available : 
                    self.frames[i]['labels']['userSurveyRating'] = self.frames[i]['labels']['userSurveyRating']\
                        if self.frames[i]['labels']['userSurveyRating'] else 0
                    # Filtering only highest quality interactions - threshold set to 4 for now - then iterating through reference data : 
                    if self.frames[i]['labels']['userSurveyRating']>=4:
                        for i in range(len(data)): 
                            for elt in data[i]['args']:
                                if 'key' in elt.keys() and 'val' in elt.keys() : 
                                    if elt['key'] in self.entity_keys : 
                                        args_dict[elt['key']] = elt['val']
                                        args_list.append(args_dict)
                        training_list.append({'text' : text,
                                            'intent_name' : name,
                                            'entity_labels' : [
                                            self.get_example_label(text, key, value) for key, value in args_dict.items()
                                        ]
                                        }
                                    )
        self.utterances = training_list
        return training_list, args_list

    def build_training_dict_v2(self, noref = False):
        training_list = []
        args_list = []
        # for each conversation : 
        for i in range(len(self.frames)):
            # For each turn : 
            for n in range(len(self.frames[i]['turns'])): 
                if self.frames[i]['turns'][n]['labels']['acts']:
                    if self.frames[i]['turns'][n]['labels']['acts'][0]['name']:
                        if noref : 
                            name = self.frames[i]['turns'][n]['labels']['acts_without_refs'][0]['name']
                        else:
                            name = self.frames[i]['turns'][n]['labels']['acts'][0]['name']
                    else:
                        name ="unknown"
                else:
                    name = "unknown"
                text = self.frames[i]['turns'][n]['text']
                if noref : 
                    data = self.frames[i]['turns'][n]['labels']['acts_without_refs']
                else : 
                    data = self.frames[i]['turns'][n]['labels']['acts']
                args_dict = {}
                # Imputing with value zero where no surveyrating is available : 
                self.frames[i]['labels']['userSurveyRating'] = self.frames[i]['labels']['userSurveyRating']\
                    if self.frames[i]['labels']['userSurveyRating'] else 0 
                # Filtering only highest quality interactions - threshold set to 4 for now - then iterating through reference data : 
                if self.frames[i]['labels']['userSurveyRating']>=4:
                    for q in range(len(data)): 
                        for elt in data[q]['args']:
                            if 'key' in elt.keys() and 'val' in elt.keys() : 
                                if elt['key'] in self.entity_keys : 
                                    args_dict[elt['key']] = elt['val']
                                    args_list.append(args_dict)
                    training_list.append({'text' : text,
                                        'intent_name' : name,
                                        'entity_labels' : [
                                        self.get_example_label(text, key, value) for key, value in args_dict.items()
                                    ]
                                    }
                                )
        self.utterances = training_list            
        return training_list, args_list
    
    # Train:test split function : 
    def split_data(self, split_ratio=0.8): 
        split_idx = math.ceil(len(self.utterances)*split_ratio)
        self.trainset = self.utterances[:split_idx]
        self.testset = self.utterances[split_idx:]
    
    def split_data_v2(self, input_dict, split_ratio=0.8):
        self.trainset = {}
        self.testset = {}
        for key in input_dict.keys() :
            split_idx = math.ceil(len(input_dict[key])*split_ratio)
            self.trainset[key] = input_dict[key][:split_idx]
            self.testset[key] = input_dict[key][split_idx:]    
            
    # Main function creating, passing data to, training and publishing LUIS app
    def create_app_v2(self, split=True, app_name=None, version_id=None):
        try:
            # Create a LUIS app
            default_app_name = "FlymeLuis-{}".format(datetime.datetime.now())
            default_version_id = "2.0"
            app_name = default_app_name if not app_name else app_name
            version_id = default_version_id if not version_id else version_id
            print("Creating App {}, version {}".format(
                default_app_name, version_id))
            self.app_id = self.client.apps.add({
                'name': default_app_name,
                'initial_version_id': version_id,
                'description': "New App created with LUIS Python sample",
                'culture': 'en-us',
            })
            print("Created app {}".format(self.app_id))
            # Create entities for the model
            print(f"\nWe'll create {len(self.entity_keys)} new entities for our flyme MVP inputs.")
            for key in self.entity_keys : 
                entity_id = self.client.model.add_entity(self.app_id, version_id, name=key)
                time.sleep(0.2)
                print("{} simple entity created with id {}".format(key, entity_id))
            print("\nWe'll create a new intent for each of Microsoft Frames dataset 'acts' names")
            # build utterances from dataset
            self.build_training_dict_v2()
            # Sending trainset by batches of 50 conversations : 
            sorted_utterances = {}
            all_intents = [x['intent_name'] for x in self.utterances]
            intents_unique = [x for i, x in enumerate(all_intents) if i == all_intents.index(x)]
            if not self.intent_keys :
                self.intent_keys = intents_unique 
            # Create model intents based upon intents found in input dataset
            for i in range(len(intents_unique)):
                intent_id = self.client.model.add_intent(
                    self.app_id,
                    version_id,
                    intents_unique[i]
                )
                time.sleep(0.2)
                print("{} intent created with id {}".format(
                    intents_unique[i], intent_id
                ))
                sorted_utterances[intents_unique[i]] = [self.utterances[n] for n in range(len(self.utterances)) if (self.utterances[n]['intent_name'] == intents_unique[i])]
            # Split data stratifying proportion of examples for each intent
            if split:
                self.split_data_v2(sorted_utterances)
            else:
                self.split_data_v2(sorted_utterances, split_ratio = 1)
            # Add example batches to model 
            for key in self.trainset.keys():
                if len(self.trainset[key]) > 90 : 
                    if len(self.trainset[key]) > 1500 :
                        # Examples over idx 1500 will not be sent to prevent model fitting issues 
                        for n in range(30): 
                            i = 50 * n
                            self.client.examples.batch(self.app_id, version_id, self.trainset[key][i:i+50])
                            time.sleep(0.2)
                        print(f"\nUtterances added to the {key} intent")
                    else:
                        # Batch all example by 50 before sending
                        for n in range((len(self.trainset[key])//50)) : 
                            i = 50 * n
                            self.client.examples.batch(self.app_id, version_id, self.trainset[key][i:i+50])
                            time.sleep(0.2)
                        print(f"\nUtterances added to the {key} intent")
                else : 
                    # Send all examples in one batch
                    self.client.examples.batch(self.app_id, version_id, self.trainset[key])
                    print(f"\nUtterances added to the {key} intent")
                    time.sleep(0.2)
            # Training the model
            print("\nWe'll start training your app...")
            async_training = self.client.train.train_version(self.app_id, version_id)
            is_trained = async_training.status == "UpToDate"
            trained_status = ["UpToDate", "Success"]
            while not is_trained:
                time.sleep(1)
                status = self.client.train.get_status(self.app_id, version_id)
                is_trained = all(
                    m.details.status in trained_status for m in status)
            print("Your app is trained. You can now go to the LUIS portal and test it!")

            # Publish the app
            print("\nWe'll start publishing your app...")
            publish_result = self.client.apps.publish(self.app_id,
                                                version_id=version_id,
                                                is_staging=False
                                                )
            self.prediction_endpoint = publish_result.endpoint_url
            test_url = publish_result.endpoint_url + \
                "?subscription-key=" + self.subscription_key + "&q="
            print("Your app is published. You can now go to test it on\n{}".format(test_url))

        except Exception as err:
            print("Encountered exception. {}".format(err))

    def test_app(self, prediction_key=None, scores=False):
        # Testing function - will evaluate testset if prediction endpoint key is passed, 
        # else will use authoring endpoint credentials to test 5 utterances
        if prediction_key:
            endpoint_url = self.prediction_endpoint[:-52]
            runtimeCredentials = CognitiveServicesCredentials(prediction_key)
            test_size = sum([len(self.testset[key]) for key in self.testset.keys()])
        else:
            endpoint_url = self.authoring_endpoint
            runtimeCredentials = CognitiveServicesCredentials(self.subscription_key)
            test_size = 5
        # Instantiate client then send a prediction request for each utterance
        clientRuntime = LUISRuntimeClient(endpoint=endpoint_url, credentials=runtimeCredentials)
        results = {} 

        if test_size > 500:
            sample = 0 
            for key in self.testset.keys():
                for utterance in range(len(self.testset[key])):
                    req = self.testset[key][utterance]['text']
                    luis_result = clientRuntime.prediction.resolve(self.app_id, req)
                    results[self.testset[key][utterance]['text']] = LuisUtil.luis_result_as_dict(luis_result) if luis_result else {}
                    time.sleep(0.2)
                    sample+=1
                    if sample >= test_size:
                        break
                if sample >= test_size:
                    break
        else:
            assessed = {} 
            for key in self.testset.keys():
                assessed[key] = [] 
            while len(results) < test_size:
                key = random.choice(list(self.testset.keys()))
                utterance = random.choice(range(len(self.testset[key])))
                assessed[key].append(self.testset[key][utterance])
                req = self.testset[key][utterance]['text']
                luis_result = clientRuntime.prediction.resolve(self.app_id, req)
                results[self.testset[key][utterance]['text']] = LuisUtil.luis_result_as_dict(luis_result) if luis_result else {}
                time.sleep(0.2)
        # Compute and return Metrics if required : 
        if scores:
            if test_size > 500:
                assessed = self.testset
            return results, self.f1_score_v2(self.entity_keys, self.intent_keys, assessed, results)
        else:
            return results
    
    @staticmethod
    def f1_score (base_list, testset, predictions):
        # Initiating result storage dict: 
        tn = tp = fn = fp = 0
        results_dict = {}
        results_dict ["global"] = {"fn":0, "fp":0, "tn":0, "tp":0}
        for base_type in base_list : 
            results_dict[base_type] = {"fn":0, "fp":0, "tn":0, "tp":0}
        print(f'testset length : {len(testset)}')
        print(f'predictions length : {len(predictions)}')
        index_shift = 0
        # Iterating through reference and detected entities for each sentence - index_shift will compensate for invalid/missing luis results
        for utterance, prediction in enumerate(list(predictions.values())):
            idx = utterance + index_shift
            # skip utterance from reference dict and increase index shift if not equal to detected utterance
            if testset[idx]["text"] != prediction["query"]:
                index_shift += 1
            # if equal, increment relevant counters in results dict : 
            else:
                reference_entities = [i["entity_name"] for i in testset[idx]["entity_labels"]]
                detected_entities = [i["type"]for i in prediction["entities"]]
                for base_type in base_list : 
                    if base_type in reference_entities : 
                        if base_type in detected_entities:
                            tp+=1
                            results_dict["global"]["tp"]+=1
                            results_dict[base_type]["tp"]+=1
                        else:
                            fn+=1
                            results_dict["global"]["fn"]+=1
                            results_dict[base_type]["fn"]+=1
                    else:
                        if base_type in detected_entities:
                            fp+=1
                            results_dict["global"]["fp"]+=1
                            results_dict[base_type]["fp"]+=1
                        else:
                            tn+=1
                            results_dict["global"]["tn"]+=1
                            results_dict[base_type]["tn"]+=1
        print(f"tp : {tp}, tn : {tn}, fp : {fp}, fn : {fn}")
        # Calculate metrics based on 
        for key in results_dict:
            results_dict[key]["Precision"] = results_dict[key]["tp"] / (results_dict[key]["tp"] + results_dict[key]["fn"])
            results_dict[key]["Recall"] = results_dict[key]["tp"] / (results_dict[key]["tp"] + results_dict[key]["fp"])
            results_dict[key]["F1_score"] = 2 * (results_dict[key]["Precision"] * results_dict[key]["Recall"]) / \
            (results_dict[key]["Precision"] + results_dict[key]["Recall"])
        print(f'Precision average : {results_dict["global"]["Precision"]}\n' + \
              f'Recall average : {results_dict["global"]["Recall"]}\nF1 score : {results_dict["global"]["F1_score"]}')
        return results_dict
    @staticmethod
    def f1_score_v2 (entity_base_list, intent_base_list, testset, predictions):
        # Initiating result storage dict: 
        intent_tp = intent_tn = intent_fp = intent_fn = entity_tp = entity_tn = entity_fp = entity_fn = 0
        results_dict = {}
        results_dict ["global_entity_recognition"] = {"fn":0, "fp":0, "tn":0, "tp":0}
        results_dict ["global_intent_recognition"] = {"fn":0, "fp":0, "tn":0, "tp":0}
        results_dict["entities"]={}
        results_dict["intents"]={}
        for entity_base_type in entity_base_list : 
            results_dict["entities"][entity_base_type] = {"fn":0, "fp":0, "tn":0, "tp":0}
        for intent_base_type in intent_base_list : 
            results_dict["intents"][intent_base_type] = {"fn":0, "fp":0, "tn":0, "tp":0}
        print(f'testset length : {sum([len(testset[key]) for key in testset.keys()])}')
        print(f'predictions length : {len(predictions)}')
        index_shift = 0
        zipper = []
        buff = [[(key, ind) for ind in range(len(testset[key]))]for key in testset.keys()]
        for n in range(len(buff)) : 
            for q in range(len(buff[n])):
                zipper.append(buff[n][q])
        # Iterating through reference and detected entities for each sentence - index_shift will compensate for invalid/missing luis results
        for utterance, prediction in enumerate(list(predictions.values())):
            idx = utterance + index_shift
            # For debugging : 
            # print(f"now handling test #{utterance}, Text location in set : {zipper[idx]}")
            
            # skip utterance from reference dict and increase index shift if not equal to detected utterance
            if idx >= len(predictions):
                break
            if testset[zipper[idx][0]][zipper[idx][1]]["text"] != prediction["query"]:
                index_shift += 1
            # if equal, increment relevant counters in results dict : 
            else:
                reference_entities = [i["entity_name"] for i in testset[zipper[idx][0]][zipper[idx][1]]["entity_labels"]]
                detected_entities = [i["type"]for i in prediction["entities"]]
                reference_intent = testset[zipper[idx][0]][zipper[idx][1]]["intent_name"]
                detected_intent = prediction["topScoringIntent"]['intent']
                for entity_base_type in entity_base_list : 
                    if entity_base_type in reference_entities : 
                        if entity_base_type in detected_entities:
                            entity_tp+=1
                            results_dict["global_entity_recognition"]["tp"] = results_dict["global_entity_recognition"].get("tp") + 1
                            results_dict["entities"][entity_base_type]["tp"] = results_dict["entities"][entity_base_type].get("tp") + 1
                        else:
                            entity_fn+=1
                            results_dict["global_entity_recognition"]["fn"] = results_dict["global_entity_recognition"].get("fn") + 1
                            results_dict["entities"][entity_base_type]["fn"] = results_dict["entities"][entity_base_type].get("fn") + 1
                    else:
                        if entity_base_type in detected_entities:
                            entity_fp+=1
                            results_dict["global_entity_recognition"]["fp"] = results_dict["global_entity_recognition"].get("fp") + 1
                            results_dict["entities"][entity_base_type]["fp"] = results_dict["entities"][entity_base_type].get("fp") + 1
                        else:
                            entity_tn+=1
                            results_dict["global_entity_recognition"]["tn"] = results_dict["global_entity_recognition"].get("tn") + 1
                            results_dict["entities"][entity_base_type]["tn"] = results_dict["entities"][entity_base_type].get("tn") + 1
                
                for intent_base_type in intent_base_list : 
                    if intent_base_type == reference_intent : 
                        if intent_base_type == detected_intent:
                            intent_tp+=1
                            results_dict["global_intent_recognition"]["tp"]+=1
                            results_dict["intents"][intent_base_type]["tp"]+=1
                        else:
                            intent_fn+=1
                            results_dict["global_intent_recognition"]["fn"]+=1
                            results_dict["intents"][intent_base_type]["fn"]+=1
                    else:
                        if intent_base_type == detected_intent:
                            intent_fp+=1
                            results_dict["global_intent_recognition"]["fp"]+=1
                            results_dict["intents"][intent_base_type]["fp"]+=1
                        else:
                            intent_tn+=1
                            results_dict["global_intent_recognition"]["tn"]+=1
                            results_dict["intents"][intent_base_type]["tn"]+=1
        print(f"Intent detection scores : \n\ntp : {intent_tp}, tn : {intent_tn}, fp : {intent_fp}, fn : {intent_fn}\n")
        print(f"Entity detection scores : \n\ntp : {entity_tp}, tn : {entity_tn}, fp : {entity_fp}, fn : {entity_fn}\n")
        
        
        # Calculate metrics based on 
        for key in ["global_intent_recognition", "global_entity_recognition"]:
            if (results_dict[key]["tp"] + results_dict[key]["fn"]) == 0:
                results_dict[key]["Precision"] =0
            else:
                results_dict[key]["Precision"] = results_dict[key]["tp"] / (results_dict[key]["tp"] + results_dict[key]["fn"])
            if (results_dict[key]["tp"] + results_dict[key]["fp"]) == 0 : 
                results_dict[key]["Recall"] = 0
            else:
                results_dict[key]["Recall"] = results_dict[key]["tp"] / (results_dict[key]["tp"] + results_dict[key]["fp"])
            if (results_dict[key]["Precision"] + results_dict[key]["Recall"]) == 0:
                results_dict[key]["F1_score"] = 0
            else:
                results_dict[key]["F1_score"] = 2 * (results_dict[key]["Precision"] * results_dict[key]["Recall"]) / \
                (results_dict[key]["Precision"] + results_dict[key]["Recall"])
        for key in results_dict["intents"].keys() : 
            print(f"{key} : {results_dict['intents'][key]}")
            if ((results_dict["intents"][key]["tp"] + results_dict["intents"][key]["fn"]) ==0):
                results_dict["intents"][key]["Precision"] = 0
            else :
                results_dict["intents"][key]["Precision"] = (results_dict["intents"][key]["tp"] / (results_dict["intents"][key]["tp"] + results_dict["intents"][key]["fn"]))
            if ((results_dict["intents"][key]["tp"] + results_dict["intents"][key]["fp"])==0):
                results_dict["intents"][key]["Recall"] = 0
            else : 
                results_dict["intents"][key]["Recall"] = (results_dict["intents"][key]["tp"] / (results_dict["intents"][key]["tp"] + results_dict["intents"][key]["fp"]))
            if (results_dict["intents"][key]["Recall"] + results_dict["intents"][key]["Precision"]) == 0:
                results_dict["intents"][key]["F1_score"] = 0
            else:
                results_dict["intents"][key]["F1_score"] = 2 * (results_dict["intents"][key]["Precision"] * results_dict["intents"][key]["Recall"]) / \
                (results_dict["intents"][key]["Precision"] + results_dict["intents"][key]["Recall"])
        for key in results_dict["entities"].keys():
            if (results_dict["entities"][key]["tp"] + results_dict["entities"][key]["fn"]) == 0 : 
                results_dict["entities"][key]["Precision"]=0
            else:
                results_dict["entities"][key]["Precision"] = results_dict["entities"][key]["tp"] / (results_dict["entities"][key]["tp"] + results_dict["entities"][key]["fn"])
            if (results_dict["entities"][key]["tp"] + results_dict["entities"][key]["fp"]) == 0 : 
                results_dict["entities"][key]["Recall"]=0
            else:
                results_dict["entities"][key]["Recall"] = results_dict["entities"][key]["tp"] / (results_dict["entities"][key]["tp"] + results_dict["entities"][key]["fp"])
            if (results_dict["entities"][key]["Precision"] + results_dict["entities"][key]["Recall"]) == 0 :
                results_dict["entities"][key]["F1_score"]=0
            else:
                results_dict["entities"][key]["F1_score"] = 2 * (results_dict["entities"][key]["Precision"] * results_dict["entities"][key]["Recall"]) / \
                (results_dict["entities"][key]["Precision"] + results_dict["entities"][key]["Recall"])

        print(f'-------------- Intents Results -------------\n\nPrecision average : {results_dict["global_intent_recognition"]["Precision"]}\n' + \
              f'Recall average : {results_dict["global_intent_recognition"]["Recall"]}\nF1 score : {results_dict["global_intent_recognition"]["F1_score"]}\n')
        print(f'-------------- Entity Results -------------\n\nPrecision average : {results_dict["global_entity_recognition"]["Precision"]}\n' + \
              f'Recall average : {results_dict["global_entity_recognition"]["Recall"]}\nF1 score : {results_dict["global_entity_recognition"]["F1_score"]}')
        return results_dict
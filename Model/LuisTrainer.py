from azure.cognitiveservices.language.luis.authoring import LUISAuthoringClient
from azure.cognitiveservices.language.luis.runtime import LUISRuntimeClient
from botbuilder.ai.luis.luis_util import LuisUtil
import datetime
import math
from msrest.authentication import CognitiveServicesCredentials
import time


SUBSCRIPTION_KEY_ENV_NAME = "LUIS_AUTHORING_KEY"

class LuisAppCreator:

    def __init__(self, luis_authoring_key,
    frames, 
    entity_keys=['or_city', 'dst_city', 'str_date', 'end_date', 'budget'],
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
        self.authoring_endpoint='https://flymeluis.cognitiveservices.azure.com/'
        self.prediction_endpoint = None
        self.app_id = None

    def get_example_label(self, statement, entity_name, value):
                statement = statement.lower()
                value = value.lower()
                return {
                    'entity_name': entity_name,
                    'start_char_index': statement.find(value),
                    'end_char_index': statement.find(value) + len(value)
                }

    def build_training_dict(self, noref = False):
        training_list = []
        args_list = []
        for i in range(len(self.frames)):
            for n in self.frames[i]['turns']: 
                if 'text' in n.keys():
                    text = n['text']
                    if noref : 
                        data = n['labels']['acts_without_refs']
                    else : 
                        data = n['labels']['acts']
                    args_dict = {}
                    # Imputing zeros where no surveyrating is available : 
                    self.frames[i]['labels']['userSurveyRating'] = self.frames[i]['labels']['userSurveyRating']\
                        if self.frames[i]['labels']['userSurveyRating'] else 0
                    # Filtering only highest quality interactions, threshold 4 for now : 
                    if self.frames[i]['labels']['userSurveyRating']>=4:
                        for i in range(len(data)): 
                            for elt in data[i]['args']:
                                if 'key' in elt.keys() and 'val' in elt.keys() : 
                                    if elt['key'] in self.entity_keys : 
                                        args_dict[elt['key']] = elt['val']
                                        args_list.append(args_dict)
                        training_list.append({'text' : text,
                                            'intent_name' : "book",
                                            'entity_labels' : [
                                            self.get_example_label(text, key, value) for key, value in args_dict.items()
                                        ]
                                        }
                                    )
        self.utterances = training_list
        return training_list, args_list

    def split_dict(self, split_ratio=0.8): 
        split_idx = math.ceil(len(self.utterances)*split_ratio)
        self.trainset = self.utterances[:split_idx]
        self.testset = self.utterances[split_idx:]

    def booking_app(self, split=True):
        """Authoring.
        This will create a LUIS Booking application, train and publish it.
        """
        try:
            # Create a LUIS app
            default_app_name = "FlymeLuis-{}".format(datetime.datetime.now())
            version_id = "0.1"

            print("Creating App {}, version {}".format(
                default_app_name, version_id))

            self.app_id = self.client.apps.add({
                'name': default_app_name,
                'initial_version_id': version_id,
                'description': "New App created with LUIS Python sample",
                'culture': 'en-us',
            })
            print("Created app {}".format(self.app_id))

            # Add information into the model

            print(f"\nWe'll create {len(self.entity_keys)} new entities for our flyme MVP inputs.")
            for key in self.entity_keys : 
                destination_name = key
                destination_id = self.client.model.add_entity(self.app_id, version_id, name=destination_name)
                print("{} simple entity created with id {}".format(destination_name, destination_id))

            print("\nWe'll create a new \"book\" intent including the trainset utterances:")
            intent_name = "book"
            intent_id = self.client.model.add_intent(
                self.app_id,
                version_id,
                intent_name
            )
            print("{} intent created with id {}".format(
                intent_name,
                intent_id
            ))
            self.build_training_dict()
            if split:
                self.split_dict()
            else:
                self.trainset = self.utterances
            # Sending trainset by batches of 50 conversations : 
            for n in range((len(self.trainset)//50)-1) : 
                i = 50 * n
                self.client.examples.batch(self.app_id, version_id, self.trainset[i:i+50])
                time.sleep(0.2)
            print("\nUtterances added to the {} intent".format(intent_name))
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
        # If prediction key is not provided, use authoring key to test just a few examples 
        if prediction_key:
            endpoint_url = self.prediction_endpoint[:-52]
            runtimeCredentials = CognitiveServicesCredentials(prediction_key)
            test_size = len(self.testset)
        
        else:
            endpoint_url = self.authoring_endpoint
            runtimeCredentials = CognitiveServicesCredentials(self.subscription_key)
            test_size = 5
        
        clientRuntime = LUISRuntimeClient(endpoint=endpoint_url, credentials=runtimeCredentials)
        results = {}
        for utterance in range(test_size): 
            req = self.testset[utterance]['text']
            luis_result = clientRuntime.prediction.resolve(self.app_id, req)
            prediction = LuisUtil.luis_result_as_dict(luis_result) if luis_result else {}
            results[self.testset[utterance]['text']] = prediction
            time.sleep(0.2)
        if scores:
            return results, self.f1_score(self.entity_keys, self.testset[:test_size], results)
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
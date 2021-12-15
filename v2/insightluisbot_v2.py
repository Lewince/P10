# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from botbuilder.core import ActivityHandler, TurnContext, RecognizerResult, ConversationState, UserState, turn_context
from botbuilder.schema import ChannelAccount
# from botbuilder.dialogs import DialogSet, WaterfallDialog, WaterfallStepContext
# from botbuilder.dialogs.prompts import TextPrompt, NumberPrompt, DateTimePrompt, PromptOptions
from data_map import ConState, UserProfile, EnumUser, EnumQuestion
import datetime
from dateparser import parse
import regex as re
from botbuilder.ai.luis import LuisApplication, LuisPredictionOptions, LuisRecognizer
from botbuilder.ai.luis.luis_util import LuisUtil


class InsightLuisBot_v2(ActivityHandler):
    def __init__(self, constate:ConversationState, userstate:UserState,
    appid, appkey, logger, verbose=False):
        self.constate = constate
        self.userstate = userstate
        self.conprop = self.constate.create_property("constate")
        self.userprop = self.userstate.create_property("userstate")
        self.logger = logger
        self.luis_app = LuisApplication(
            appid,
            appkey,
            "https://westeurope.api.cognitive.microsoft.com/")
        self.luisapp_entity_types = ['or_city','dst_city', 'simple_city', 'str_date', 'end_date', 'simple_date', 'budget']
        luis_options = LuisPredictionOptions(include_all_intents=True, include_instance_data=True)
        self.luis_rec = LuisRecognizer(self.luis_app, luis_options, True)
        self.verbose = verbose
    
    # add state saving and AppInsights logging to superclass on_turn method
    async def on_turn(self, turn_context:TurnContext):
        await super().on_turn(turn_context)
        await self.constate.save_changes(turn_context)
        await self.userstate.save_changes(turn_context)
        self.logger.warning(turn_context.activity.text)

    # Upon new user arrival, start conversation by sending welcome message and invite 
    async def on_members_added_activity(self,
        members_added: ChannelAccount,
        turn_context: TurnContext):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome! My name is FlyMeBot and I am here to help you book your trip.\nTo start with, could you please give me a few details on the flights you are looking for?")


    # Process user reply to previous turn and send invite based on missing information : 
    async def on_message_activity(self, turn_context: TurnContext):
        conmode = await self.conprop.get(turn_context, ConState())
        usermode = await self.userprop.get(turn_context, UserProfile())
        if self.verbose : 
            print("\n-------------New message received from user--------------\n")
            print(f"Current context value : {conmode.qtoken}")
        luis_result = await self.luis_rec.recognize(turn_context)    
        if luis_result is not None:
            result_dict = LuisUtil.luis_result_as_dict(luis_result)
            if self.verbose : 
                print('luis result OK')
                print(result_dict)
        else:
            if self.verbose : 
                print('luis result NOK - filling dummy dict')
            result_dict = {'entities' : {'dummykey': {'dummykey':'Empty'}}}
        await self.process_intents(conmode, usermode, turn_context, result_dict)    

    async def process_intents(self, conmode, usermode, turn_context, result_dict):
        if result_dict['intents']['Greet']['score'] >= 0.9:
            await turn_context.send_activity("Hello again! So what kind of trip shall I search for you?")
        elif result_dict['intents']['Communication_Confirm']['score'] >= 0.9:
            await turn_context.send_activity("Thanks for confirming! We will now search for tickets matching your criteria")
        elif result_dict['intents']['Utilities_Reject']['score'] >= 0.9:
            await turn_context.send_activity("I'm sorry I could not understand your request properly - Can you please rephrase that?")
            self.logger.error("User notified Understanding Issue")
        elif result_dict['intents']['Utilities_Cancel']['score'] >= 0.9:
            await turn_context.send_activity("Your search was cancelled - Thanks for using FlyMeBot")
        elif result_dict['intents']['Utilities_StartOver']['score'] >= 0.9:
            usermode.orig = ""
            usermode.dest = ""
            usermode.depdate = ""
            usermode.retdate = ""
            usermode.budget = ""
            conmode.profile = EnumUser.LUIS
            await turn_context.send_activity("OK let us start this all over : can you please give me some details about the trip you are searching for")
        # Extract entities from results dict if intent is "book"
        elif result_dict['intents']['book']['score'] >= 0.9:
            # extract entities from results dict : 
            await self.extract_entities(result_dict, usermode, conmode)
            # Send summary
            if self.verbose:
                print(f"found entities so far : {usermode.orig}, {usermode.dest}, {usermode.depdate}, {usermode.retdate}, {usermode.budget}")
            if not (usermode.orig !="" and usermode.dest !="" and usermode.depdate!="" and usermode.retdate!="" and usermode.budget!=""):
                summary = f'I gathered following information so far : \n\nOrigin city : {usermode.orig if usermode.orig!="" else "missing"}' \
                    + f'\n\nDestination city : {usermode.dest if (usermode.dest!="") else "missing"}'\
                    + f'\n\nDeparture date : {usermode.depdate if (usermode.depdate!="") else "missing"}' \
                    + f'\n\nReturn date : {usermode.retdate if (usermode.retdate!="") else "missing"}'\
                    + f'\n\nAllowed budget in $ : {usermode.budget if (usermode.budget!="") else "missing"}'
                await turn_context.send_activity(summary)
            # Set conversation status End turn sending appropriate new invite or question
            self.update_conmode_to_reflect_missing_values(conmode, usermode)
            await self.set_statii_and_send_targeted_questions(conmode, usermode, turn_context)
        else : 
            await turn_context.send_activity("I did not understand that, can you please rephrase?")
            self.logger.error("Unclear Intent from Recognizer - Lower P thresholds or improve Laguage Understanding Model")

    # Extract Intents and entities from results dict - log error message if issue with LU results
    async def extract_entities(self, result_dict, usermode, conmode):
        for i in result_dict['entities'].keys():
            if i == 'dummykey' :
                print("Action needed : LUIS results dict with dummy key was provided for entity extraction")
                await turn_context.send_activity("Sorry, an error occurred - how can I help you again ?")
                self.logger.error("LUIS App result was None - ACTION REQUIRED on LUIS app or credentials")
            elif isinstance(result_dict['entities'][i], dict):
                if self.verbose:
                    print('luis_result_dict_OK')
                for key in result_dict['entities'][i].keys():
                    if self.verbose:
                        print(f"now processing key {key}")
                    if (key in self.luisapp_entity_types) : 
                        if self.verbose:
                            print(f"{key} is valid")
                        entity = result_dict['entities'][i][key]
                        if (result_dict['entities'][i][key][0]['score'] >= 0.5):
                            # out_string = f"Entity detected : \n Name : {key}, Value : {entity[0]['text']}, " + f"Probability : {entity[0]['score']:.3} \n"                            
                            if (key == "or_city") : 
                                usermode.orig = re.sub(r'\W+', '', entity[0]['text'])
                            elif (key == "dst_city") : 
                                usermode.dest = re.sub(r'\W+', '', entity[0]['text'])
                            elif (key == "str_date") : 
                                usermode.depdate = str(parse(entity[0]['text'],
                                settings={'PREFER_DATES_FROM': 'future'}).date())
                            elif (key == "end_date") : 
                                usermode.retdate = str(parse(entity[0]['text'],
                                settings={'PREFER_DATES_FROM': 'future'}).date())
                            elif (key == "budget") : 
                                usermode.budget = re.sub(r'[^\d]', '', entity[0]['text'])
                            elif (key == "simple_date") : 
                                if conmode.qtoken == EnumQuestion.DEPDATE:
                                    usermode.depdate = str(parse(entity[0]['text'],
                                    settings={'PREFER_DATES_FROM': 'future'}).date())
                                elif conmode.qtoken == EnumQuestion.RETDATE:
                                    usermode.retdate = str(parse(entity[0]['text'],
                                    settings={'PREFER_DATES_FROM': 'future'}).date())
                            elif (key == "simple_city") : 
                                if conmode.qtoken == EnumQuestion.ORIG:
                                    usermode.orig = re.sub(r'\W+', '', entity[0]['text'])
                                elif conmode.qtoken == EnumQuestion.DEST:
                                    usermode.dest = re.sub(r'\W+', '', entity[0]['text'])
                        else:
                            if self.verbose : 
                                print(f"entity {key} has insufficient P")
                            self.logger.error("Relevant entities found but with low P - no prediction will be supplied")
                            # out_string = "no probable entity found"    
                    else:
                        if self.verbose:
                            print(f"key found but invalid")
                        self.logger.error("None of relevant entities were found - no prediction to supply - "\
                            + "check if all entities are addressed in class entity list")
                    # await turn_context.send_activity(out_string)
            else:
                if self.verbose:
                    print("missed entity recognition - result object is not a dict")
                self.logger.error("No result available from LUIS App")
                # await turn_context.send_activity("missed - not a dict")

    def update_conmode_to_reflect_missing_values(self, conmode, usermode):
        if usermode.orig == "":
            if self.verbose:
                print("Now routing to origin question")
            conmode.profile = EnumUser.ORIG
        elif usermode.dest == "":
            if self.verbose:
                print("Now routing to destination question")
            conmode.profile = EnumUser.DEST
        elif usermode.depdate == "":
            if self.verbose:
                print("Now routing to departure date question")
            conmode.profile = EnumUser.DEPDATE
        elif usermode.retdate == "":
            if self.verbose:
                print("Now routing to return date question")
            conmode.profile = EnumUser.RETDATE
        elif usermode.budget == "":
            if self.verbose:
                print("Now routing to budget question")
            conmode.profile = EnumUser.BUDGET
        else :
            if self.verbose:
                print("Now routing to confirmation question")
            conmode.profile = EnumUser.DONE

    async def set_statii_and_send_targeted_questions(self, conmode, usermode, turn_context) : 
        if(conmode.profile == EnumUser.ORIG):
            await turn_context.send_activity("Where would you like to depart from ?")
            conmode.qtoken = EnumQuestion.ORIG
            if self.verbose:
                print('origin question sent')
            conmode.profile = EnumUser.LUIS
        elif(conmode.profile == EnumUser.DEST):
            await turn_context.send_activity("Where would you like to travel to ?")
            conmode.qtoken = EnumQuestion.DEST
            if self.verbose:
                print('destination question sent')
            conmode.profile = EnumUser.LUIS
        elif(conmode.profile == EnumUser.DEPDATE):
            if self.verbose:
                print("depdate question sent")
            await turn_context.send_activity("Please provide desired departure date")
            conmode.qtoken = EnumQuestion.DEPDATE
            conmode.profile = EnumUser.LUIS       
        elif(conmode.profile == EnumUser.RETDATE):
            await turn_context.send_activity("Please provide desired return date") 
            conmode.qtoken = EnumQuestion.RETDATE
            if self.verbose:
                print("return date question sent")
            conmode.profile = EnumUser.LUIS
        elif(conmode.profile == EnumUser.BUDGET):
            await turn_context.send_activity("How much can you spend on these tickets?") 
            conmode.qtoken = EnumQuestion.BUDGET
            if self.verbose:
                print('budget question sent')
            conmode.profile = EnumUser.LUIS
        elif(conmode.profile == EnumUser.DONE):
            await self.end_check_and_messages(conmode, usermode, turn_context)

# Actions taken when all travel details are collected : 
    async def end_check_and_messages(self, conmode, usermode, turn_context: TurnContext):
        if self.check_dates_validity(parse(usermode.depdate), parse(usermode.retdate))[0] :
            if self.verbose:
                print('Info complete')
            info = "Information appears to be complete, please check below summary and confirm : \n"\
                + "\n\nOrigin city : " + usermode.orig + "\n\nDestination city : " + usermode.dest + "\n\nDeparture date : " + usermode.depdate + "\n\nReturn date : " + usermode.retdate + "\n\nAllowed budget in $ : " + usermode.budget
            await turn_context.send_activity(info)
            conmode.qtoken = EnumQuestion.DONE
            conmode.profile = EnumUser.LUIS
        elif self.check_dates_validity(parse(usermode.depdate), parse(usermode.retdate))[1] == "dates too far":
            await turn_context.send_activity("One or more of your travelling dates are too far - we can only search and book flights within a period of 2 years. Could I search other dates for this trip?")
            conmode.qtoken = EnumQuestion.LUIS
            conmode.profile = EnumUser.LUIS
        elif self.check_dates_validity(parse(usermode.depdate), parse(usermode.retdate))[1] == "delta over 6 months":
            await turn_context.send_activity("The time span between your departure and return flights is over 6 months - For many reasons including visa and residency titles, we do not operate round trips on such time spans. Please provide dates within timespan range")
            conmode.qtoken = EnumQuestion.LUIS
            conmode.profile = EnumUser.LUIS
        elif self.check_dates_validity(parse(usermode.depdate), parse(usermode.retdate))[1] == "negative delta":
            await turn_context.send_activity("return date is anterior to departure date. Please reformulate your traveling dates. ")
            conmode.qtoken = EnumQuestion.LUIS
            conmode.profile = EnumUser.LUIS
        elif self.check_dates_validity(parse(usermode.depdate), parse(usermode.retdate))[1] == "invalid departure":
            await turn_context.send_activity("Your departure date is invalid. Please restate")
            conmode.qtoken = EnumQuestion.DEPDATE
            conmode.profile = EnumUser.LUIS
        elif self.check_dates_validity(parse(usermode.depdate), parse(usermode.retdate))[1] == "invalid return":
            await turn_context.send_activity("Your return date is invalid. Please restate")
            conmode.qtoken = EnumQuestion.RETDATE
            conmode.profile = EnumUser.LUIS

    # Verify that dates make sense( in the past, too far ahead, too distant, return before departure...)
    @staticmethod
    def check_dates_validity (departure_date, return_date) : 
        today = datetime.date.today()
        valid = False
        if departure_date.date() > today:
            term = departure_date.date() - today
            if (term.days>730) : 
                text_output = "dates too far"
            elif return_date.date() > today :
                term = return_date.date() - today
                if (term.days>730) : 
                    text_output = "dates too far"
                elif return_date.date() > departure_date.date() : 
                    delta = return_date - departure_date
                    if delta.days > 182 : 
                        text_output = "delta over 6 months"
                    else:
                        valid = True
                        text_output = "OK"
                else: 
                    text_output = "negative delta"
            else:
                text_output = "invalid return"
        else:
            text_output = "invalid departure"
        return (valid, text_output)
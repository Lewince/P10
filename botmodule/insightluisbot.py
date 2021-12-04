# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Text
from botbuilder.core import ActivityHandler, TurnContext, RecognizerResult, ConversationState, UserState
from botbuilder.schema import ChannelAccount
# from botbuilder.dialogs import DialogSet, WaterfallDialog, WaterfallStepContext
# from botbuilder.dialogs.prompts import TextPrompt, NumberPrompt, DateTimePrompt, PromptOptions
from data_map import ConState, UserProfile, EnumUser
from botbuilder.ai.luis import LuisApplication, LuisPredictionOptions, LuisRecognizer
from botbuilder.ai.luis.luis_util import LuisUtil
import os

class InsightLuisBot(ActivityHandler):
    def __init__(self, constate:ConversationState, userstate:UserState,appid , appkey, logger):
        self.constate = constate
        self.userstate = userstate
        self.conprop = self.constate.create_property("constate")
        self.userprop = self.userstate.create_property("userstate")
        self.luis_app = LuisApplication(
            appid,
            appkey,
            "https://westeurope.api.cognitive.microsoft.com/")
        luis_options = LuisPredictionOptions(include_all_intents=True, include_instance_data=True)
        self.luis_rec = LuisRecognizer(self.luis_app, luis_options, True)
        self.logger = logger

    async def on_turn(self, turn_context:TurnContext):
        await super().on_turn(turn_context)
        await self.constate.save_changes(turn_context)
        await self.userstate.save_changes(turn_context)
        self.logger.warning(turn_context.activity.text)

    async def on_message_activity(self, turn_context: TurnContext):
        conmode = await self.conprop.get(turn_context, ConState())
        usermode = await self.userprop.get(turn_context, UserProfile())
        luisapp_entities_list = ['or_city','dst_city', 'str_date', 'end_date', 'budget']
        print("entering LUIS conmode phase with no info available")
        luis_result = await self.luis_rec.recognize(turn_context)
        if luis_result is not None:
            print('luis result OK')
            result_dict = LuisUtil.luis_result_as_dict(luis_result)
            print(result_dict)
        else:
            print('luis result NOK')
            result_dict = {'entities' : {'dummykey': {'dummykey':'Empty'}}}
        if result_dict['intents']['Communication_Confirm']['score'] >= 0.9:
            await turn_context.send_activity("Thanks for confirming! We will now search for tickets matching your criteria")
        elif result_dict['intents']['Utilities_Reject']['score'] >= 0.9:
            await turn_context.send_activity("I'm sorry I could not understand your request properly - Can you please rephrase the incorrect part?")
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
            await turn_context.send_activity("OK let us start this all over : can you please give me some details about the trip you wish to book?")
        elif result_dict['intents']['book']['score'] >= 0.9:
            for i in result_dict['entities'].keys():
                if i == 'dummykey' :
                    await turn_context.send_activity("I might have missed something there - how can I help you again ?")
                elif isinstance(result_dict['entities'][i], dict):
                    print('luis_result_dict_OK')
                    for key in result_dict['entities'][i].keys():
                        print(f"now processing key {key}")
                        if (key in luisapp_entities_list) : 
                            print(f"{key} is valid")
                            entity = result_dict['entities'][i][key]
                            if (result_dict['entities'][i][key][0]['score'] >= 0.5):
                                # out_string = f"Entity detected : \n Name : {key}, Value : {entity[0]['text']}, " + f"Probability : {entity[0]['score']:.3} \n"                            
                                if (key == "or_city") : 
                                    usermode.orig = entity[0]['text']
                                elif (key == "dst_city") : 
                                    usermode.dest = entity[0]['text']
                                elif (key == "str_date") : 
                                    usermode.depdate = entity[0]['text']
                                elif (key == "end_date") : 
                                    usermode.retdate = entity[0]['text']
                                elif (key == "budget") : 
                                    usermode.budget = entity[0]['text']
                            else:
                                print(f"entity {key} has insufficient P")
                                self.logger.error("Relevant entities found but with low P - no prediction will be supplied")
                                # out_string = "no probable entity found"    
                        else:
                            print(f"key found but invalid")
                            self.logger.error("None of relevant entities were found - no prediction to supply")
                        # await turn_context.send_activity(out_string)
                else:
                    print("missed entity recognition - result object is not a dict")
                    self.logger.error("No result available from LUIS App")
                    # await turn_context.send_activity("missed - not a dict")
            print(f"found entities : {usermode.orig}, {usermode.dest}, {usermode.depdate}, {usermode.retdate}, {usermode.budget}")
            if not (usermode.orig !="" and usermode.dest !="" and usermode.depdate!="" and usermode.retdate!="" and usermode.budget!=""):
                loopmsg = f'I gathered following information so far : \n\nOrigin city : {usermode.orig if usermode.orig!="" else "missing"}' \
                    + f'\n\nDestination city : {usermode.dest if (usermode.dest!="") else "missing"}'\
                    + f'\n\nDeparture date : {usermode.depdate if (usermode.depdate!="") else "missing"}' \
                    + f'\n\nReturn date : {usermode.retdate if (usermode.retdate!="") else "missing"}'\
                    + f'\n\nAllowed budget in $ : {usermode.budget if (usermode.budget!="") else "missing"}'
                await turn_context.send_activity(loopmsg)

            if usermode.orig == "":
                print("step 1 - Now routing to origin question")
                conmode.profile = EnumUser.ORIG
            elif usermode.dest == "":
                print("step 1 - Now routing to destination question")
                conmode.profile = EnumUser.DEST
            elif usermode.depdate == "":
                print("step 1 - Now routing to departure date question")
                conmode.profile = EnumUser.DEPDATE
            elif usermode.retdate == "":
                print("step 1 - Now routing to return date question")
                conmode.profile = EnumUser.RETDATE
            elif usermode.budget == "":
                print("step 1 - Now routing to budget question")
                conmode.profile = EnumUser.BUDGET
            else :
                print("step 1 - Now routing to confirmation question")
                conmode.profile = EnumUser.DONE

            if(conmode.profile == EnumUser.ORIG):
                await turn_context.send_activity("Where would you like to depart from ?")
                print('origin question sent')
                conmode.profile = EnumUser.LUIS
            elif(conmode.profile == EnumUser.DEST):
                await turn_context.send_activity("Where would you like to travel to ?")
                print('destination question sent')
                conmode.profile = EnumUser.LUIS
            elif(conmode.profile == EnumUser.DEPDATE):
                print("depdate question sent")
                await turn_context.send_activity("Please provide desired departure date")
                conmode.profile = EnumUser.LUIS       
            elif(conmode.profile == EnumUser.RETDATE):
                await turn_context.send_activity("Please provide desired return date") 
                print("return date question sent")
                conmode.profile = EnumUser.LUIS
            elif(conmode.profile == EnumUser.BUDGET):
                await turn_context.send_activity("How much can you spend on these tickets?") 
                print('budget question sent')
                conmode.profile = EnumUser.LUIS
            elif(conmode.profile == EnumUser.DONE):
                print('step 1 - info complete')
                info = "Information appears to be complete, please check below summary and confirm : \n"\
                    + "\n\nOrigin city : " + usermode.orig + "\n\nDestination city : " + usermode.dest + "\n\nDeparture date : " + usermode.depdate + "\n\nReturn date : " + usermode.retdate + "\n\nAllowed budget in $ : " + usermode.budget
                await turn_context.send_activity(info)
                conmode.profile = EnumUser.LUIS
        else : 
            await turn_context.send_activity("I did not understand your intent, can you please rephrase that?")
            self.logger.error("Unclear Intent from Recognizer - Lower P thresholds or improve Laguage Understanding Model")
    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome to FlyMe, my name is FlyMeBot and I am here to help you book your trip!\nPlease deliver some details on the trip you want to book")

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Text
from botbuilder.core import ActivityHandler, TurnContext, RecognizerResult, ConversationState, UserState
from botbuilder.schema import ChannelAccount
from data_map import ConState, UserProfile, EnumUser
from botbuilder.ai.luis import LuisApplication, LuisPredictionOptions, LuisRecognizer
from botbuilder.ai.luis.luis_util import LuisUtil



class LuisBot(ActivityHandler):
    def __init__(self, luis_appid, luis_key):
        self.luis_app = LuisApplication(
            luis_appid,
            luis_key,
            "https://westeurope.api.cognitive.microsoft.com/")
        luis_options = LuisPredictionOptions(include_all_intents=True, include_instance_data=True)
        self.luis_rec = LuisRecognizer(self.luis_app, luis_options, True)

    async def on_message_activity(self, turn_context: TurnContext):
        luis_result = await self.luis_rec.recognize(turn_context)
        if luis_result : 
            intent = self.luis_rec.top_intent(luis_result)
            result = luis_result.properties["luisResult"]
            result_dict = LuisUtil.luis_result_as_dict(luis_result)
        else:
            intent = "Empty"
            result_dict = {'entities' : {'dummykey': {'dummykey':'Empty'}}}
        
        await turn_context.send_activity(f"top_intent : {intent}")
        
        for i in result_dict['entities'].keys():
            if i == 'dummykey' :
                await turn_context.send_activity("Hi I am FlyMeBot Booking Agent how can I help you ?")
            elif  isinstance(result_dict['entities'][i], dict):
                for key in result_dict['entities'][i].keys():
                    if result_dict['entities'][i][key][0]['score'] >= 0.5:
                        entity = result_dict['entities'][i][key]
                        out_string = f"Entity name : {key}, Value : {entity[0]['text']}, " + f"Probability : {entity[0]['score']} \n"                            
                    await turn_context.send_activity(out_string)


class StatefulLuisBot(ActivityHandler):
    def __init__(self, constate:ConversationState, userstate:UserState, luis_appid, luis_appkey):
        self.constate = constate
        self.userstate = userstate
        self.conprop = self.constate.create_property("constate")
        self.userprop = self.userstate.create_property("userstate")
        self.luis_app = LuisApplication(
            luis_appid,
            luis_appkey,
            "https://westeurope.api.cognitive.microsoft.com/")
        luis_options = LuisPredictionOptions(include_all_intents=True, include_instance_data=True)
        self.luis_rec = LuisRecognizer(self.luis_app, luis_options, True)

    async def on_turn(self, turn_context:TurnContext):
        await super().on_turn(turn_context)

        await self.constate.save_changes(turn_context)
        await self.userstate.save_changes(turn_context)

    async def on_message_activity(self, turn_context: TurnContext):
        conmode = await self.conprop.get(turn_context, ConState())
        usermode = await self.userprop.get(turn_context, UserProfile())
        luisapp_entities_list = ['or_city','dst_city', 'str_date', 'ret_date', 'budget']
        if(conmode.profile == EnumUser.ORIG):
            usermode.orig = turn_context.activity.text
            print('origin was saved')
            conmode.profile = EnumUser.LUIS
        if(conmode.profile == EnumUser.DEST):
            usermode.dest = turn_context.activity.text
            print('destination was saved')
            conmode.profile = EnumUser.LUIS
        if(conmode.profile == EnumUser.DEPDATE):
            print("now saving depdate")
            usermode.depdate = turn_context.activity.text
            conmode.profile = EnumUser.LUIS          
        if(conmode.profile == EnumUser.RETDATE):
            print("now saving ret date")
            usermode.retdate = turn_context.activity.text
            print(f"saved return date {usermode.retdate}")
            conmode.profile = EnumUser.LUIS
        if(conmode.profile == EnumUser.BUDGET):
            usermode.budget = turn_context.activity.text
            conmode.profile = EnumUser.LUIS
            print('origin was saved')
        if(conmode.profile == EnumUser.DONE):
            info = "Information appears to be complete, please check below summary and confirm : "\
                + "\n\nOrigin city : " + usermode.orig + "\n\nDestination city : " + usermode.dest + "\n\nDeparture date : " + usermode.depdate + "\n\nReturn date : " + usermode.retdate + "\n\nAllowed budget in $ : " + usermode.budget
            await turn_context.send_activity(info)
            conmode.profile = EnumUser.LUIS

        if(conmode.profile == EnumUser.LUIS) and not (usermode.orig !="" or usermode.dest !="" or usermode.depdate!="" or usermode.retdate!="" or usermode.budget!=""):
            print("entering LUIS conmode phase with no info available")
            luis_result = await self.luis_rec.recognize(turn_context)
            if luis_result is not None:
                print('luis result OK')
                result_dict = LuisUtil.luis_result_as_dict(luis_result)
                print(result_dict)
            else:
                print('luis result NOK')
                result_dict = {'entities' : {'dummykey': {'dummykey':'Empty'}}}
            if result_dict['intents']['book']['score'] >= 0.9:
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
                                    out_string = f"Entity detected : \n Name : {key}, Value : {entity[0]['text']}, " + f"Probability : {entity[0]['score']:.3} \n"                            
                                    if (key == "or_city") : 
                                        usermode.orig = entity[0]['text']
                                    elif (key == "dst_city") : 
                                        usermode.dest = entity[0]['text']
                                    elif (key == "str_date") : 
                                        usermode.depdate = entity[0]['text']
                                    elif (key == "ret_date") : 
                                        usermode.retdate = entity[0]['text']
                                    elif (key == "budget") : 
                                        usermode.budget = entity[0]['text']
                                else:
                                    print(f"entity {key} has insufficient P")
                                    out_string = "no probable entity found"    
                            else:
                                print(f"key found but invalid")
                            print("Made it to the end of luis function map!")
                            await turn_context.send_activity(out_string)
                    else:
                        print("missed entity recognition - result object is not a dict")
                        # await turn_context.send_activity("missed - not a dict")
            print(f"found entities : {usermode.orig}, {usermode.dest}, {usermode.depdate}, {usermode.retdate}, {usermode.budget}")
            await turn_context.send_activity(f'Found so far : \n\nOrigin : {usermode.orig}\n\n Destination : {usermode.dest}\n\n Departure date : {usermode.depdate}\n\n Return date : {usermode.retdate}\n\n budget : {usermode.budget}')

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
            elif(conmode.profile == EnumUser.DEST):
                await turn_context.send_activity("Where would you like to travel to ?")
                print('destination question sent')
            elif(conmode.profile == EnumUser.DEPDATE):
                print("depdate question sent")
                await turn_context.send_activity("Please provide desired departure date")       
            elif(conmode.profile == EnumUser.RETDATE):
                await turn_context.send_activity("Please provide desired return date") 
                print("return date question sent")
            elif(conmode.profile == EnumUser.BUDGET):
                await turn_context.send_activity("How much can you spend on these tickets?") 
                print('origin question sent')
            elif(conmode.profile == EnumUser.DONE):
                print('step 1 - info complete')
                info = "Information appears to be complete, please check below summary and confirm : \n"\
                    + "\n\nOrigin city : " + usermode.orig + "\n\nDestination city : " + usermode.dest + "\n\nDeparture date : " + usermode.depdate + "\n\nReturn date : " + usermode.retdate + "\n\nAllowed budget in $ : " + usermode.budget
                await turn_context.send_activity(info)
                conmode.profile = EnumUser.LUIS

        if(conmode.profile == EnumUser.LUIS) and (usermode.orig !="" or usermode.dest !="" or usermode.depdate!="" or usermode.retdate!="" or usermode.budget!=""):
            
            print("entering LUIS conmode phase with booking info available")
            if not (usermode.orig !="" and usermode.dest !="" and usermode.depdate!="" and usermode.retdate!="" and usermode.budget!=""):
                loopmsg = f'I gathered following information so far : \n\nOrigin city : {usermode.orig if usermode.orig!="" else "missing"}' \
                    + f'\n\nDestination city : {usermode.dest if (usermode.dest!="") else "missing"}'\
                    + f'\n\nDeparture date : {usermode.depdate if (usermode.depdate!="") else "missing"}' \
                    + f'\n\nReturn date : {usermode.retdate if (usermode.retdate!="") else "missing"}'\
                    + f'\n\nAllowed budget in $ : {usermode.budget if (usermode.budget!="") else "missing"}'
                await turn_context.send_activity(loopmsg)
            
            if usermode.orig == "":
                print("step 2 - Now routing to origin question")
                conmode.profile = EnumUser.ORIG
            elif usermode.dest == "":
                print("step 2 - Now routing to destination question")
                conmode.profile = EnumUser.DEST
            elif usermode.depdate == "":
                print("step 2 - Now routing to departure date question")
                conmode.profile = EnumUser.DEPDATE
            elif usermode.retdate == "":
                print("step 2 - Now routing to return date question")
                conmode.profile = EnumUser.RETDATE
            elif usermode.budget == "":
                print("step 2 - Now routing to budget question")
                conmode.profile = EnumUser.BUDGET
            else :
                print("step 2 - Now routing to confirmation question")
                conmode.profile = EnumUser.DONE

            if(conmode.profile == EnumUser.ORIG):
                await turn_context.send_activity("Where would you like to depart from ?")
                print('origin question sent')
            elif(conmode.profile == EnumUser.DEST):
                await turn_context.send_activity("Where would you like to travel to ?")
                print('destination question sent')
            elif(conmode.profile == EnumUser.DEPDATE):
                print("depdate question sent")
                await turn_context.send_activity("Please provide desired departure date")       
            elif(conmode.profile == EnumUser.RETDATE):
                await turn_context.send_activity("Please provide desired return date") 
                print("return date question sent")
            elif(conmode.profile == EnumUser.BUDGET):
                await turn_context.send_activity("How much can you spend on these tickets?") 
                print('origin question sent')
            elif(conmode.profile == EnumUser.DONE):
                print('step 1 - info complete')
                info = "Information appears to be complete, please check below summary and confirm : \n"\
                    + "\nOrigin city : " + usermode.orig + "\nDestination city : " + usermode.dest + "\nDeparture date : " + usermode.depdate + "\nReturn date : " + usermode.retdate + "\nAllowed budget in $ : " + usermode.budget
                await turn_context.send_activity(info)
                conmode.profile = EnumUser.LUIS

    async def on_members_added_activity(
        self,
        members_added: ChannelAccount,
        turn_context: TurnContext
    ):
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome to FlyMeChat, my name is FlyMeBot and I am here to help you book your trip!\nPlease deliver some details on the trip you want to book")

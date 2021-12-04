# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

from typing import Text
from botbuilder.core import ActivityHandler, TurnContext, ConversationState, MessageFactory
from botbuilder.schema import ChannelAccount
from botbuilder.dialogs import DialogSet, WaterfallDialog, WaterfallStepContext
from botbuilder.dialogs.prompts import TextPrompt, NumberPrompt, DateTimePrompt, PromptOptions
from data_map import ConState, UserProfile, EnumUser

class DialogBot(ActivityHandler):
    
    def __init__(self, constate:ConversationState): 
        self.constate = constate
        self.state_prop = self.constate.create_property("dialog_set")
        self.dialog_set = DialogSet(self.state_prop)
        self.dialog_set.add(TextPrompt("text_prompt"))
        self.dialog_set.add(NumberPrompt("number_prompt"))
        self.dialog_set.add(DateTimePrompt("datetime_prompt"))
        self.dialog_set.add(WaterfallDialog("main_dialog", [self.GetOrigin, self.GetDestination, self.GetDepDate, self.GetRetDate, self.GetBudget, self.Completed]))

    async def GetOrigin(self, w_step:WaterfallStepContext):
        return await w_step.prompt("text_prompt", PromptOptions(prompt=MessageFactory.Text("Please enter departure airport")))

    async def GetDestination(self, w_step:WaterfallStepContext):
        return await w_step.prompt("text_prompt", PromptOptions(prompt=MessageFactory.Text("Please enter destination airport")))

    async def GetDepDate(self, w_step:WaterfallStepContext):
        return await w_step.prompt("datetime_prompt", PromptOptions(prompt=MessageFactory.Text("Please enter desired departure date")))

    async def GetRetDate(self, w_step:WaterfallStepContext):
        return await w_step.prompt("datetime_prompt", PromptOptions(prompt=MessageFactory.Text("Please enter desired return date")))
    
    async def GetBudget(self, w_step:WaterfallStepContext):
        return await w_step.prompt("number_prompt", PromptOptions(prompt=MessageFactory.Text("Please enter maximum budget in dollars")))

    async def Completed(self, w_step:WaterfallStepContext):
        return await w_step.end_dialog()

    async def on_turn(self, turn_context:TurnContext):
        dialog_context = await self.dialog_set.create_context(turn_context)
        if (dialog_context.active_dialog is not None):
            await dialog_context.continue_dialog()
        else:
            await dialog_context.begin_dialog("main_dialog")
        await self.constate.save_changes(turn_context)

    # async def on_members_added_activity(
    #     self,
    #     members_added: ChannelAccount,
    #     turn_context: TurnContext
    # ):
    #     for member_added in members_added:
    #         if member_added.id != turn_context.activity.recipient.id:
    #             await turn_context.send_activity("Hello and welcome!")

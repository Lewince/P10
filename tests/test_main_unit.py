# add bot module to system path if operated from its own working directory else import will fail
import sys
import pathlib
app_dir = pathlib.Path(__file__).parent
sys.path.append(str(app_dir))
# Import test components
from botbuilder.core.adapters.test_adapter import TestFlow
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    TurnContext,
    ConversationState,
    UserState,
    MemoryStorage
)
from botbuilder.core.adapters import TestAdapter, TestFlow
from botbuilder.dialogs import DialogSet, DialogTurnStatus
from botbuilder.dialogs.prompts import (
    AttachmentPrompt, 
    PromptOptions, 
    PromptValidatorContext
)
from botbuilder.schema import Activity, ActivityTypes, Attachment
from botmodule import InsightLuisBot
from config import DefaultConfig
from dateparser import parse
import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler
import unittest
import aiounittest

memstore = MemoryStorage()
constate = ConversationState(memstore)
userstate = UserState(memstore)
name = __name__


class Test_Bot_Activities_Test(aiounittest.AsyncTestCase):
    
    def setUp(self, constate=constate, userstate=userstate, config=DefaultConfig(), name=name):
        super().setUp()
        self.CONFIG = config
        logger = logging.getLogger(name)
        logger.addHandler(AzureLogHandler(
            connection_string=self.CONFIG.INSIGHTS_CSTRING)
        )
        self.bot = InsightLuisBot(constate, userstate, self.CONFIG.LUIS_APP_ID, self.CONFIG.LUIS_KEY, logger)
    
    def test_check_config_test(self):
        self.assertEqual(type(self.CONFIG.LUIS_APP_ID), str)
        self.assertTrue(len(self.CONFIG.LUIS_APP_ID) == 36)
        self.assertEqual(type(self.CONFIG.LUIS_KEY), str)
        self.assertTrue(len(self.CONFIG.LUIS_KEY) == 32)
        self.assertEqual(type(self.CONFIG.INSIGHTS_CSTRING), str)
        self.assertTrue(len(self.CONFIG.INSIGHTS_CSTRING) == 55)
        self.assertEqual(type(self.CONFIG.APP_ID), str)
        self.assertTrue(len(self.CONFIG.APP_ID) == 36)
        self.assertEqual(type(self.CONFIG.APP_PASSWORD), str)
        self.assertTrue(len(self.CONFIG.APP_PASSWORD) == 32)

    def test_check_date_validator_test(self):
        self.assertEqual(self.bot.check_dates_validity(parse("november 15 2022"), parse("december 15 2022")), (True, "OK"))
        self.assertEqual(self.bot.check_dates_validity(parse("november 15 2021"), parse("january 15 2022")), (False, "invalid departure"))
        self.assertEqual(self.bot.check_dates_validity(parse("february 15 2022"), parse("november 15 2021")), (False, "invalid return"))
        self.assertEqual(self.bot.check_dates_validity(parse("january 15 2023"), parse("november 15 2022")), (False, "negative delta"))
        self.assertEqual(self.bot.check_dates_validity(parse("january 15 2022"), parse("november 15 2022")), (False, "delta over 6 months"))
        self.assertEqual(self.bot.check_dates_validity(parse("december 01 2023"), parse("january 15 2024")), (False, "dates too far"))
        self.assertEqual(self.bot.check_dates_validity(parse("december 01 2024"), parse("december 5 2024")), (False, "dates too far"))

    async def test_element_greeting_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("Hi there!", "Hello again! So what kind of trip shall I search for you?")

    async def test_element_rejection_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("No", "I'm sorry I could not understand your request properly - Can you please reformulate your request?")

    async def test_element_confirmation_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("Yes!", "Thanks for confirming! We will now search for tickets matching your criteria")

    async def test_element_start_over_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("please start over", "OK let us start this all over : can you please give me some details about the trip you wish to book?")

    async def test_element_cancel_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("cancel", "Your search was cancelled - Thanks for using FlyMeBot")

    async def test_full_dialog_1_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        mylongstring = "I gathered following information so far : \n\nOrigin city : paris\n\nDestination city : seattle\n\nDeparture date : missing\n\nReturn date : missing\n\nAllowed budget in $ : missing"
        test_flow = TestFlow(None, adapter)
        tf_2 = await test_flow.send("Hello I want to go from Paris to Seattle please!")
        tf_3 = await tf_2.assert_reply(mylongstring)
        tf_4 = await tf_3.assert_reply("Please provide desired departure date")     
        tf_5 = await tf_4.send("I can leave on february 4")
        tf_6 = await tf_5.assert_reply("I gathered following information so far : \n\nOrigin city : paris\n\nDestination city : seattle\n\nDeparture date : 2022-02-04\n\nReturn date : missing\n\nAllowed budget in $ : missing")
        tf_7 = await tf_6.assert_reply("Please provide desired return date")
        tf_8 = await tf_7.send("return on march 6 please")
        tf_9 = await tf_8.assert_reply("I gathered following information so far : \n\nOrigin city : paris\n\nDestination city : seattle\n\nDeparture date : 2022-02-04\n\nReturn date : 2022-03-06\n\nAllowed budget in $ : missing")
        tf_10 = await tf_9.assert_reply("How much can you spend on these tickets?")
        tf_11 = await tf_10.send("I could spend 1600 $")
        tf_12 = await tf_11.assert_reply("Information appears to be complete, please check below summary and confirm : \n\n\nOrigin city : paris\n\nDestination city : seattle\n\nDeparture date : 2022-02-04\n\nReturn date : 2022-03-06\n\nAllowed budget in $ : 1600")
        tf_13 = await tf_12.send("that's correct")
        await tf_13.assert_reply("Thanks for confirming! We will now search for tickets matching your criteria")


# class Test_Components_Method(unittest.TestCase):
    
#     def setUp(self):
#         self.CONFIG = DefaultConfig()
#         self.logger = logging.getLogger(name)
#         self.logger.addHandler(AzureLogHandler(
#             connection_string=self.CONFIG.INSIGHTS_CSTRING)
#         )
#         self.bot = InsightLuisBot(constate, userstate, self.CONFIG.LUIS_APP_ID, self.CONFIG.LUIS_KEY, self.logger)
    
#     def test_config_test(self):
#         self.assertEqual(type(self.CONFIG.LUIS_APP_ID), str)
#         self.assertTrue(len(self.CONFIG.LUIS_APP_ID) == 36)
#         self.assertEqual(type(self.CONFIG.LUIS_KEY), str)
#         self.assertTrue(len(self.CONFIG.LUIS_KEY) == 32)
#         self.assertEqual(type(self.CONFIG.INSIGHTS_CSTRING), str)
#         self.assertTrue(len(self.CONFIG.INSIGHTS_CSTRING) == 55)
#         self.assertEqual(type(self.CONFIG.APP_ID), str)
#         self.assertTrue(len(self.CONFIG.APP_ID) == 36)
#         self.assertEqual(type(self.CONFIG.APP_PASSWORD), str)
#         self.assertTrue(len(self.CONFIG.APP_PASSWORD) == 32)

#     def test_check_date_validator_test(self):
#         self.assertEqual(self.bot.check_dates_validity(parse("november 15 2022"), parse("december 15 2022")), (True, "OK"))
#         self.assertEqual(self.bot.check_dates_validity(parse("november 15 2021"), parse("january 15 2022")), (False, "invalid departure"))
#         self.assertEqual(self.bot.check_dates_validity(parse("february 15 2022"), parse("november 15 2021")), (False, "invalid return"))
#         self.assertEqual(self.bot.check_dates_validity(parse("january 15 2023"), parse("november 15 2022")), (False, "negative delta"))
#         self.assertEqual(self.bot.check_dates_validity(parse("january 15 2022"), parse("november 15 2022")), (False, "delta over 6 months"))
#         self.assertEqual(self.bot.check_dates_validity(parse("december 01 2023"), parse("january 15 2024")), (False, "dates too far"))
#         self.assertEqual(self.bot.check_dates_validity(parse("december 01 2024"), parse("december 5 2024")), (False, "dates too far"))


if __name__ == '__main__':
    unittest.main(verbosity=2)

# add bot module to system path if operated from its own working directory else import will fail
import sys
import pathlib
app_dir = pathlib.Path(__file__).parent.parent
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

class Test_Azure_Check_Resource_Credentials_Test(aiounittest.AsyncTestCase):
    def setUp(self, config=DefaultConfig()):
        super().setUp()
        self.CONFIG = config
    def test_a_luis_app_id_test(self):
        self.assertEqual(type(self.CONFIG.LUIS_APP_ID), str)
        self.assertTrue(len(self.CONFIG.LUIS_APP_ID) == 36)
    def test_b_luis_prediction_key_test(self):
        self.assertEqual(type(self.CONFIG.LUIS_KEY), str)
        self.assertTrue(len(self.CONFIG.LUIS_KEY) == 32)
    def test_c_app_insights_conn_string_test(self):
        self.assertEqual(type(self.CONFIG.INSIGHTS_CSTRING), str)
        self.assertTrue(len(self.CONFIG.INSIGHTS_CSTRING) == 55)
    def test_d_bot_application_id_test(self):
        self.assertEqual(type(self.CONFIG.APP_ID), str)
        self.assertTrue(len(self.CONFIG.APP_ID) == 36)
    def test_e_bot_app_password_test(self):
        self.assertEqual(type(self.CONFIG.APP_PASSWORD), str)
        self.assertTrue(len(self.CONFIG.APP_PASSWORD) == 32)

class Test_Bot_Activities_Test(aiounittest.AsyncTestCase):
    # To instantiate class, setUp method subrogates __init__ method (protected against overriding in aiounittest)
    def setUp(self, constate=constate, userstate=userstate, config=DefaultConfig(), name=name):
        super().setUp()
        self.CONFIG = config
        logger = logging.getLogger(name)
        logger.addHandler(AzureLogHandler(
            connection_string=self.CONFIG.INSIGHTS_CSTRING)
        )
        self.bot = InsightLuisBot(constate, userstate, self.CONFIG.LUIS_APP_ID, self.CONFIG.LUIS_KEY, logger)
    # Below methods will check that dates validator returns expected outputs 
    # for each possible case of conditional structure
    def test_f_check_dates_validator_OK_test(self):
        self.assertEqual(self.bot.check_dates_validity(parse("november 15 2022"), parse("december 15 2022")), (True, "OK"))
    
    def test_g_check_dates_validator_departure_in_past_test(self):    
        self.assertEqual(self.bot.check_dates_validity(parse("november 15 2021"), parse("january 15 2022")), (False, "invalid departure"))
    
    def test_h_check_dates_OK_validator_return_in_past_test(self):
        self.assertEqual(self.bot.check_dates_validity(parse("february 15 2022"), parse("november 15 2021")), (False, "invalid return"))
    
    def test_i_check_dates_validator_departure_later_than_return_test(self):
        self.assertEqual(self.bot.check_dates_validity(parse("january 15 2023"), parse("november 15 2022")), (False, "negative delta"))
    
    def test_j_check_dates_validator_stay_over_6_months_test(self):
        self.assertEqual(self.bot.check_dates_validity(parse("january 15 2022"), parse("november 15 2022")), (False, "delta over 6 months"))
    
    def test_k_check_dates_validator_return_too_far_test(self):
        self.assertEqual(self.bot.check_dates_validity(parse("december 01 2023"), parse("january 15 2024")), (False, "dates too far"))
    
    def test_l_check_dates_validator_both_dates_too_far_test(self):
        self.assertEqual(self.bot.check_dates_validity(parse("december 01 2024"), parse("december 5 2024")), (False, "dates too far"))
    
    # Below async methods will send a simple message that clearly reflects one of modelled intents
    # Will pass if trained LUIS model runs and of course if bot conditional logic remains unchanged
    async def test_m_element_greeting_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("Hi there!", "Hello again! So what kind of trip shall I search for you?")

    async def test_n_element_rejection_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("No", "I'm sorry I could not understand your request properly - Can you please reformulate your request?")

    async def test_o_element_confirmation_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("Yes!", "Thanks for confirming! We will now search for tickets matching your criteria")

    async def test_p_element_start_over_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("please start over", "OK let us start this all over : can you please give me some details about the trip you wish to book?")

    async def test_q_element_cancel_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        await adapter.test("cancel", "Your search was cancelled - Thanks for using FlyMeBot")
    
    # Below method will test a full conversation based on sentences containing most basic 
    # context elements. This dialog is known to work as soon as model is trained, 
    # hence expected replies will not change unless model or conversational logic change as well. 
    async def test_z_full_dialog_1_test(self):
        adapter = TestAdapter(self.bot.on_turn)
        test_flow = TestFlow(None, adapter)
        tf_2 = await test_flow.send("Hello I want to go from Paris to Seattle please!")
        tf_3 = await tf_2.assert_reply("I gathered following information so far : \n\nOrigin city : paris\n\nDestination city : seattle\n\nDeparture date : missing\n\nReturn date : missing\n\nAllowed budget in $ : missing")
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


if __name__ == '__main__':
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

class DefaultConfig:
    """ Bot Configuration """
    PORT = 3978 #8000 
    APP_ID = "c5874c44-5d23-46de-8c30-3f6af7f4fc06" # os.environ.get("BotAppId", "")
    APP_PASSWORD = "N/6=0:GW|HdphxUBb%W:Bykc*UEGQQHU" # os.environ.get("MicrosoftAppPassword", "")
    INSIGHTS_CSTRING = "InstrumentationKey=e9aa12c1-ec5b-4c44-b4e7-9d0f362909de" # os.environ.get("AppInsightsInstrumentationKey")
    LUIS_APP_ID = "f4fd0633-0834-4472-baca-c2f049d20d13"# os.environ.get("LUIS_APP_ID")
    LUIS_KEY = "45a9d9ca1a8d4b3396cef9fe532a4747" # os.environ.get("LUIS_SUBSCRIPTION_KEY")
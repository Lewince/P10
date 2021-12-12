#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os

class DefaultConfig:
    """ Bot Configuration """
    PORT = 8000 
    APP_ID = os.environ.get("MicrosoftAppID", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
    INSIGHTS_CSTRING = os.environ.get("AppInsightsInstrumentationKey")
    LUIS_APP_ID = os.environ.get("LUIS_APP_ID")
    LUIS_KEY = os.environ.get("LUIS_SUBSCRIPTION_KEY")
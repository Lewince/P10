from enum import Enum

class EnumUser(Enum):
    ORIG = 1
    DEST = 2
    DEPDATE = 3
    RETDATE = 4
    BUDGET = 5
    DONE = 6


class ConState:
    def __init__(self):
        self.profile = EnumUser.ORIG
    @property
    def CurrentPos(self):
        return self.profile
    @CurrentPos.setter
    def EnumUser(self, current:EnumUser):
        self.profile = current


class UserProfile:
    def __init__(self):
        self.orig = ""
        self.dest = ""
        self.depdate = ""
        self.retdate = ""
        self.budget = ""
    
    @property
    def Orig(self):
        return self.orig
    @Orig.setter
    def Orig(self, orig:str):
        self.orig = orig
    
    @property
    def Dest(self):
        return self.dest
    @Dest.setter
    def Dest(self, dest:str):
        self.dest = dest

    @property
    def Depdate(self):
        return self.depdate
    @Depdate.setter
    def Depdate(self, depdate:str):
        self.depdate = depdate

    @property
    def Retdate(self):
        return self.retdate
    @Retdate.setter
    def Retdate(self, retdate:str):
        self.retdate = retdate

    @property
    def Budget(self):
        return self.budget
    @Budget.setter
    def Budget(self, budget:str):
        self.budget = budget

   

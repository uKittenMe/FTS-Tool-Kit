# This Python file uses the following encoding: utf-8

# Title: FTS Service Toolkit Main File
# Author: Everly Larche - Integrations Specalist
# Rev: NR - WIP
# Date: 2023-11-03

# This souce is not designed to be read by the end user

################################
# Imports and required Modules #
################################

#import rc_icons
from PyQt6 import (
    QtWidgets,
    uic
)
import platform, logging, sys, datetime, os, json
from src.dbHandler import mongoHandler


###########
# Classes #
###########

class myLogger():
    pass

################

class startPopUp():
    def __init__(self):
        self.popUp = uic.loadUi(os.path.join('_internal', 'startWarning.ui'))

    def showpop(self):
        # Executing the popup holds control until the window is closed
        self.popUp.exec()

################

class mainUI():
    # Classwide variables/values
    commitData = []
    _absDIR = os.getcwd()

    # Class Setup
    def __init__(self):
        # Grab all UI elements that may be needed during startup
        self.window = uic.loadUi(os.path.join('_internal', 'mainwindow.ui'))
        self.loadSNWindow = uic.loadUi(os.path.join('_internal', 'loadSNWindow.ui'))
        self.loadSettingsWindow = uic.loadUi(os.path.join('_internal', 'settings.ui'))
        self.commitQueueWindow = uic.loadUi(os.path.join('_internal', 'commitQueue.ui'))
        self.contWindow = uic.loadUi(os.path.join('_internal', 'continue.ui'))
        self.taskCompleteWindow = uic.loadUi(os.path.join('_internal', 'doneTask.ui'))
        self.searchResults = uic.loadUi(os.path.join('_internal', 'searchResults.ui'))

        # Establish button connectors
        self.window.commitTHS.clicked.connect(lambda: self.addToQueue())
        self.window.PushtoDB.clicked.connect(lambda: self.pushToDB())
        self.commitQueueWindow.remove_from_queue.clicked.connect(lambda: self.removeFromQueue(self.commitQueueWindow.list_commit.currentRow()))
        self.loadSNWindow.buttonBox.accepted.connect(lambda: self.searchForEntry(self.loadSNWindow.sn.text()))

        #Establish toolbar connectors
        self.window.actionSettings.triggered.connect(lambda: self.showFromToolbar(signal=0))
        self.window.actionLoad_SN.triggered.connect(lambda: self.showFromToolbar(signal=1))
        self.window.actionCommit_Queue.triggered.connect(lambda: self.showFromToolbar(signal=2))

        # Other UI Set-up
        self.updateDate()
        self.window.date_of_entry.setText(self.todaysDate+" (Current)")

    ################

    # Class Functions
    def updateDate(self):
        self.todaysDate:str = datetime.datetime.today().strftime("%Y-%m-%d")

    def showUI(self):
        self.window.show()

    # to show ui/windows based on button press mapped to case#
    def showFromToolbar(self, signal):
        match signal:
            case 0:
                self.loadSettingsWindow.exec() #exec function are BLOCKING
            case 1:
                endCode:int = self.loadSNWindow.exec()
            case 2:
                displaySN = []
                for items in self.commitData:
                    displaySN.append(items["destCollection"] + " --> SN:" + items["Serial_Number"])

                print(displaySN)
                self.commitQueueWindow.list_commit.addItems(displaySN)
                self.commitQueueWindow.exec()
                self.commitQueueWindow.list_commit.clear()

    # Det. what to commit depending on tab widget index as case statement
    def addToQueue(self):
        signal:int = self.window.tabWidget.currentIndex()

        # Check if the user is sure, if not, end function do not grab data
        if self.contWindow.exec() == 0: return

        match signal:
            case 0:
                pass
            case 1:
                # Open the template JSON structures and pass it along to the functionn to be changed
                with open(os.path.join(self._absDIR, '_templateStructs', 'ths_template.json'), 'r') as jsonFile:
                            ths_template = json.loads(jsonFile.read())
                with open(os.path.join(self._absDIR, '_templateStructs', 'ths_translation.json'), 'r') as jsonFile:
                            ths_translation = json.loads(jsonFile.read())

                # Get non-itterable items first
                ths_template["Date_of_Entry"] = self.todaysDate
                ths_template["SVC_Details"]["NS_RMA"] = self.window.ns_rma.text()
                ths_template["SVC_Details"]["NS_Customer"] = self.window.ns_customer_entry.text()
                ths_template["SVC_Details"]["NS_Parts_SO"] = self.window.ns_so.text()
                ths_template["SVC_Details"]["Jira_Ticket"] = self.window.jira_ticket_entry.text()
                ths_template["SVC_Details"]["Service_Comments"] = self.window.svcComments.toPlainText()
                ths_template["SVC_Details"]["Warranty_Status"] = self.window.warranty_status.currentText()
                ths_template["SVC_Details"]["Tech"] = self.window.tech.text()

                self.getChildrenData(children=self.window.THS_scroll_area_contents.children(), template=ths_template, translation=ths_translation)
            case _:
                pass

        # Clear the fields that have already been read by the ths_template
        self.window.ns_rma.setText("RMA")
        self.window.ns_customer_entry.clear()
        self.window.ns_so.setText("SO")
        self.window.jira_ticket_entry.setText("CST-")
        self.window.svcComments.clear()
        self.window.tech.clear()

        # Preform other tasks when adding to the queue
        self.window.PushtoDB.setEnabled(True)
        self.updateDate()
        self.taskCompleteWindow.exec()

    def getChildrenData(self, children, template, translation):
        entry:dict = template
        print(type(entry))

        for child in children:
            if type(child).__name__ == "QComboBox":
                self.updateNested(entry, translation[child.objectName()], child.currentText())
            elif type(child).__name__ == "QCheckBox":
                self.updateNested(entry, translation[child.objectName()], child.isChecked())
            elif type(child).__name__ == "QLineEdit":
                self.updateNested(entry, translation[child.objectName()], child.text())
                # After getting the data, clear the field for use on another sensor
                child.clear()
            else:
                pass

            # Dont want to clear this field, but rather set it back to defualt
            self.window.ths_module_fw.setText("15")

        for x in entry:
            print(f"{x}:{entry[x]}")
        self.commitData.append(entry)

    def updateNested(self, target, targetKey, value):
        for k in target.keys():
            if targetKey == k:
                target[k] = value
                return target
            elif isinstance(target[k], dict):
                self.updateNested(target[k], targetKey, value)

    def pushToDB(self):
        # Check if the user is sure, if not, end function do not grab data
        if self.contWindow.exec() == 0: return

        db = mongoHandler()
        print(db.pushCollection(self.commitData))
        # Need to clear queue after commit and disable push to db button
        self.commitData = []
        self.window.PushtoDB.setEnabled(False)
        self.commitQueueWindow.list_commit.clear()
        self.taskCompleteWindow.exec()

    def removeFromQueue(self, index:int):
        print(index)
        self.commitQueueWindow.list_commit.takeItem(index)
        self.commitData.pop(index)
        print(self.commitData)

    def searchForEntry(self, serialNumber:str):
        print(serialNumber)
        db = mongoHandler()
        self.dbData = db.getCollection(serialNumber)
        displaySN = []
        for entry in self.dbData:
            print(entry)
            displaySN.append(entry["destCollection"] + " --> SN:" + entry["Serial_Number"] + f"  [{entry['Date_of_Entry']}]")
        self.searchResults.search_list.addItems(displaySN)
        self.searchResults.exec()
        self.searchResults.search_list.clear()





#############
# Main Loop #
#############

# Application can not be called as a deamon or child of another application
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    if platform.system() == "Windows": app.setStyle("Fusion")

    #Load UI(s)
    ui = mainUI()
    pop = startPopUp()

    # Show in order the UI windows
    pop.showpop()
    ui.showUI()
    app.exec()

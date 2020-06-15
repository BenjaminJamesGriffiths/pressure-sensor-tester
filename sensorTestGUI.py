# IMPORTS
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, QFrame
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtChart import QChart, QChartView, QValueAxis, QBarCategoryAxis, QBarSet, QBarSeries
from PyQt5.QtGui import QPainter, QFont

import sys
from datetime import datetime
import serial


class SENSOR_TEST(QWidget):
    
    bars = None
    series = None
    chart = None
    labelWidgets = []
    comms = None
    commsStatus = False
    deviceID = "HARP"

    def __init__(self):
        QWidget.__init__(self)

        # ADD GUI WIDGETS
        self.setupLayout()

        # LAUNCH GUI
        self.show()
        self.resize(800,600)

    def setupLayout(self):
        parentLayout = QVBoxLayout()
        parentLayout.setContentsMargins(20,20,20,20)

        buttonLayout = QHBoxLayout()

        # CREATE SERIAL COMMUNICATION CONNECT BUTTON
        self.connectButton = QPushButton("CONNECT")
        self.connectButton.setFixedSize(150, 40)
        self.connectButton.setCheckable(True)
        self.connectButton.setStyleSheet("QPushButton {background-color: #66BB6A; color: black; border-radius: 20px}" 
                                    "QPushButton:hover {background-color: #4CAF50; color: black; border-radius: 20px}"
                                    "QPushButton:checked {background-color: #EF5350; color: white; border-radius: 20px}"
                                    "QPushButton:checked:hover {background-color: #F44336; color: white; border-radius: 20px}")

        # CREATE SENSORS CALIBRATION BUTTON
        self.calibrateButton = QPushButton("CALIBRATE")
        self.calibrateButton.setFixedSize(150, 40)
        self.calibrateButton.setStyleSheet("QPushButton {background-color: #E0E0E0; color: black; border-radius: 20px}" 
                                    "QPushButton:hover {background-color: #BDBDBD; color: black; border-radius: 20px}" 
                                    "QPushButton:pressed {background-color: #D5D5D5; color: black; border-radius: 20px}")

        # ADD BUTTONS TO HORIZONTAL LAYOUT
        buttonLayout.addWidget(self.connectButton, alignment = Qt.AlignLeft)
        buttonLayout.addWidget(self.calibrateButton, alignment = Qt.AlignRight)
        
        # CREATE BAR CHART TO DISPLAY SENSOR READINGS
        self.bars = QBarSet('Sensor Readings')
        self.bars.append([0 for i in range(5)])
        self.chart = QChart()
        self.chart.setBackgroundRoundness(20)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)
        self.series = QBarSeries()
        self.series.append(self.bars)
        self.chart.addSeries(self.series)
        self.chart.setTitle('Sensor Readings')

        # CREATE X-AXIS AS SENSOR LABELS
        xAxis = QBarCategoryAxis()
        labels = ["Sensor {}".format(i+1) for i in range(5)]
        xAxis.append(labels)
        
        # CREATE Y-AXIS AND SENSOR READINGS
        yAxis = QValueAxis()
        yAxis.setRange(-100, 100)
        yAxis.setTickCount(11)
        yAxis.setTitleText("Pressure (%)")
        
        # ADD AXES TO CHART
        self.chart.addAxis(xAxis, Qt.AlignBottom)
        self.chart.addAxis(yAxis, Qt.AlignLeft)
        self.chart.legend().setVisible(False)

        # ATTACH AXES TO SERIES
        self.series.attachAxis(xAxis)
        self.series.attachAxis(yAxis)
        
        # ADD CHART TO A VIEW
        chartView = QChartView(self.chart)

        labelLayout = QFrame()
        labelLayout.setStyleSheet("background-color: white; border-radius: 20px")
        layout1 = QVBoxLayout()
        labelLayout.setLayout(layout1)
        layout2 = QHBoxLayout()
        layout3 = QHBoxLayout()
        
        for i in range(5):
            label = QLabel("Sensor {}".format(i+1))
            label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            label.setStyleSheet("font-weight: bold;")
            layout2.addWidget(label)

            value = QLabel("0 mV")
            value.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.labelWidgets.append(value)
            layout3.addWidget(value)

        layout1.addLayout(layout2, 1)
        layout1.addLayout(layout3, 1)

        parentLayout.addLayout(buttonLayout)
        parentLayout.addWidget(chartView, 5)
        parentLayout.addWidget(labelLayout, 1)

        # LINK WIDGETS
        self.connectButton.clicked.connect(self.serialToggle)
        self.calibrateButton.clicked.connect(self.sensorCalibrate)

        self.setLayout(parentLayout)

    def getSensorReadings(self):
        """
        PURPOSE

        Requests sensor readings from ROV and updates GUI.

        INPUT

        NONE

        RETURNS

        NONE
        """
        # SENSOR POLLING RATE (HZ)
        refreshRate = 100

        # START QTIMER TO REPEATEDLY UPDATE SENSORS AT THE DESIRED POLLING RATE 
        self.timer = QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.getSensorReadings)
        self.timer.start(int(1000*1/refreshRate))
        
        # STOP REQUESTING SENSOR VALUES IF ROV IS DISCONNECTED
        if self.commsStatus == False:
            self.timer.stop()
        
        else:
            # REQEST SINGLE READING
            sensorReadings = self.getSensors()

            # UPDATE VOLTAGE READINGS
            self.updateVoltageReadings(sensorReadings)

            # SCALE SENSOR READINGS
            scaledReadings = self.mapPressureReadings(sensorReadings)
            
            try:
                # UPDATE GUI 
                self.series.remove(self.bars)
                self.bars = QBarSet("")
                self.bars.append([float(item) for item in scaledReadings])
                self.series.append(self.bars)
            except:
                self.teensyDisconnect()

    def mapPressureReadings(self, values):
        mappedValues = []

        for value in values:
            try:
                mappedValues.append((200/1023)*float(value) - 100)
            except:
                pass

        return mappedValues

    def updateVoltageReadings(self, values):
        voltageValues = [round((3300/1023)*float(i)) for i in values]
        for i, label in enumerate(self.labelWidgets):
            label.setText(str(voltageValues[i]) + " mV")

    def serialToggle(self, buttonState):
        """
        PURPOSE

        Determines whether to connect or disconnect from the ROV serial interface.

        INPUT

        - buttonState = the state of the button (checked or unchecked).

        RETURNS

        NONE
        """
        # CONNECT
        if buttonState:
            self.teensyConnect()

        # DISCONNECT
        else:
            self.teensyDisconnect()

    def sensorCalibrate(self):
        """
        PURPOSE

        INPUT

        RETURNS

        """
        self.calibrateSensors()

    ########################
    ### SERIAL FUNCTIONS ###
    ########################
    def teensyConnect(self):
        """
        PURPOSE

        Attempts to connect to the ROV using the comms library.
        Changes the appearance of the connect buttons.
        If connection is successful, the ROV startup procedure is initiated.

        INPUT

        NONE

        RETURNS

        NONE
        """
        # DISABLE BUTTONS TO AVOID DOUBLE CLICKS
        self.connectButton.setEnabled(False)
            
        # FIND ALL AVAILABLE COM PORTS
        availableComPorts, comPort, identity = self.findComPorts(115200, self.deviceID)
        print(availableComPorts, comPort, identity)
        
        # ATTEMPT CONNECTION TO ROV COM PORT
        status, message = self.serialConnect(comPort, 115200)
        print(status, message)

        # IF CONNECTION IS SUCCESSFUL
        if status == True:
            # MODIFY BUTTON STYLE
            self.connectButton.setText('DISCONNECT')

            # START READING SENSOR VALUES
            self.getSensorReadings()
        
        # IF CONNECTION IS UNSUCCESSFUL
        else:
            self.teensyDisconnect()
            
        # RE-ENABLE CONNECT BUTTONS
        self.connectButton.setEnabled(True)

    def teensyDisconnect(self):
        """
        PURPOSE

        Disconnects from the ROV using the comms library.
        Changes the appearance of the connect buttons

        INPUT

        NONE

        RETURNS

        NONE
        """
        # MODIFY BUTTON STYLE
        self.connectButton.setText('CONNECT')
        self.connectButton.setChecked(False)
        
        # CLOSE COM PORT
        if self.commsStatus:
            self.comms.close()
            self.commsStatus = False

    def findComPorts(self, baudRate, identity):
        """
        PURPOSE

        Find all available COM ports and requests the devices identity.

        INPUT

        - menuObject = pointer to the drop down menu to display the available COM ports.
        - baudRate = baud rate of the serial interface.
        - identity = string containing the required device identity to connect to.

        RETURNS

        - availableComPorts = list of all the available COM ports.
        - rovComPort = the COM port that belongs to the device.
        - identity = the devices response from an identity request.
        """
        # CREATE LIST OF ALL POSSIBLE COM PORTS
        ports = ['COM%s' % (i + 1) for i in range(256)] 

        deviceIdentity = ""
        comPort = None
        availableComPorts = []
        
        # CHECK WHICH COM PORTS ARE AVAILABLE
        for port in ports:
            try:
                comms = serial.Serial(port, baudRate, timeout = 1)
                availableComPorts.append(port)

                # REQUEST IDENTITY FROM COM PORT
                self.commsStatus = True
                deviceIdentity = self.getIdentity(comms, identity)
                comms.close()
                self.commsStatus = False
                
                # FIND WHICH COM PORT IS THE ROV
                if deviceIdentity == identity:
                    comPort = port
                    break
                    
            # SKIP COM PORT IF UNAVAILABLE
            except (OSError, serial.SerialException):
                pass

        return availableComPorts, comPort, deviceIdentity

    def getIdentity(self, serialInterface, identity):
        """
        PURPOSE

        Request identity from a defined COM port.

        INPUT

        - serialInterface = pointer to the serial interface object.
        - identity = the desired identity response from the device connected to the COM port.

        RETURNS

        - identity = the devices response.
        """
        identity = ""
        startTime = datetime.now()
        elapsedTime = 0
        # REPEATIDELY REQUEST IDENTIFICATION FROM DEVICE FOR UP TO 3 SECONDS
        while (identity == "") and (elapsedTime < 3):
            self.serialSend("?I", serialInterface)
            identity = self.serialReceive(serialInterface)
            elapsedTime = (datetime.now() - startTime).total_seconds()

        return identity

    def serialConnect(self, comPort, baudRate):
        """
        PURPOSE

        Attempts to initialise a serial communication interface with a desired COM port.

        INPUT

        - rovComPort = the COM port of the ROV.
        - baudRate = the baud rate of the serial interface.

        RETURNS

        NONE
        """
        self.commsStatus = False
        if comPort != None:
            try: 
                self.comms = serial.Serial(comPort, baudRate, timeout = 1)
                message = "Connection to ROV successful."
                self.commsStatus = True
            except:
                message = "Failed to connect to {}.".format(comPort)
        else:
            message = "Failed to recognise device identity."

        return self.commsStatus, message

    def serialSend(self, command, serialInterface):
        """
        PURPOSE

        Sends a string down the serial interface to the ROV.

        INPUT

        - command = the command to send.
        - serialInterface = pointer to the serial interface object.

        RETURNS

        NONE
        """
        if self.commsStatus:
            try:
                serialInterface.write((command + '\n').encode('ascii'))
            except:
                self.teensyDisconnect()
                print("Failed to send command.")

    def serialReceive(self, serialInterface):
        """
        PURPOSE

        Waits for data until a newline character is received.

        INPUT

        - serialInterface = pointer to the serial interface object.

        RETURNS

        NONE
        """
        received = ""
        try:
            received = serialInterface.readline().decode('ascii').strip()
        except:
            self.teensyDisconnect()
            print("Failed to receive data.")
            
        return(received)

    def getSensors(self):
        """
        PURPOSE

        Send request to device to return sensor readings.
        
        INPUT

        NONE

        RETURNS

        - results = array containing the sensor readings.
        """
        results = []

        # REQUEST SENSOR READINGS
        command = "?S"
        self.serialSend(command, self.comms)
        
        # READ RESPONSE INTO AN ARRAY
        results = self.serialReceive(self.comms).split(",")
        print(results)
        return results

    def calibrateSensors(self):
        """
        """
        # REQUEST SENSOR READINGS
        command = "?C"
        self.serialSend(command, self.comms)

def guiInitiate():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Bahnschrift Light", 10))
    program = SENSOR_TEST()
    program.setWindowTitle("Sensor Testing Program")
    app.exec()

if __name__ == '__main__':
    guiInitiate()

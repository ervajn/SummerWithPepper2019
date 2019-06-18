from naoqi import *
import time
import sys

ROBOT_IP = '192.168.1.104'
ROBOT_PORT = 9559

HumanGreeter = None

class HumanGreeterModule(ALModule):
    """ A module to use speech recognition """
    def __init__(self, name):
        ALModule.__init__(self, name)
        self.name = name
        self.memory = ALProxy("ALMemory")
        self.tts = ALProxy("ALTextToSpeech")
        self.motion = ALProxy("ALMotion")
        self.dialog = ALProxy("ALDialog")
        self.dialog.setLanguage("English")
        self.tts.say("Im up and running")
        self.lookForHuman()

    def lookForHuman(self):
        self.tts.say("Im searching for humanoids")
        self.memory.subscribeToEvent("FaceDetected", self.name, "onFaceDetected")
        self.motion.move(0.05, 0.0, 0.0)
        self.onFaceDetected()

    def onFaceDetected(self, *_args):
        self.memory.unsubscribeToEvent("FaceDetected", self.name)
        self.tts.say("Hello humanoid")
        self.motion.stopMove()
        self.memory.subscribeToEvent("next_ride", self.name, "nextRide")
        self.memory.subscribeToEvent("trip", self.name, "trip")
        self.topic = self.dialog.loadTopic("home/nao/Snack_enu.top")
        self.dialog.subscribe(self.name)
        self.dialog.activateTopic(self.topic)

    def nextRide(self, *_args):
        self.tts.say("Here are the next rides")

    def trip(self, *_args):  # exit as of now
        self.tts.say("Where do you want to go")
        self.memory.unsubscribeToEvent("next_ride", self.name)
        self.memory.unsubscribeToEvent("trip", self.name)
        self.goal = self.memory.getData("arrStop")
        self.dep = self.memory.getData("depStop")

        self.dialog.deactivateTopic(self.topic)
        self.dialog.unloadTopic(self.topic)
        self.dialog.unsubscribe(self.name)

    def shutoff(self):
        try:
            self.memory.unsubscribeToEvent("next_ride", self.name)
            self.memory.unsubscribeToEvent("trip", self.name)
            self.dialog.deactivateTopic(self.topic)
            self.dialog.unloadTopic(self.topic)
            self.dialog.unsubscribe(self.name)
            print "Stopped dialog"
        except RuntimeError:
            pass
        try:
            self.memory.unsubscribeToEvent("FaceDetected", self.name)
            self.motion.stopMove()
            print "Unsubscribed to face and stopped walk"
        except RuntimeError:
            pass


def main():
    myBroker = ALBroker("myBroker", "0.0.0.0", 0, ROBOT_IP, ROBOT_PORT)
    global HumanGreeter
    HumanGreeter = HumanGreeterModule("HumanGreeter")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print
        print "Interrupted by user, shutting down"
        HumanGreeter.shutoff()
        myBroker.shutdown()
        sys.exit(0)


if __name__ == '__main__':
    main()